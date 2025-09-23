from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List, Set, Dict
import calendar

try:
    from .config_loader import Config
except ImportError:
    from config_loader import Config


@dataclass
class DayHours:
    """Represents hours worked on a specific date."""
    date: date
    total_hours: float
    day_hours: float  # Hours worked during day period (06:00-21:00)
    night_hours: float  # Hours worked during night period (21:00-06:00)
    is_sunday: bool
    is_holiday: bool


@dataclass
class Shift:
    post_id: str
    date: date  # Start date of shift
    start_time: time
    end_time: time
    duration_hours: int
    is_night: bool
    is_sunday: bool  # True if shift touches any Sunday
    is_holiday: bool  # True if shift touches any holiday
    shift_id: str
    # New: Hours broken down by actual working days
    hours_by_day: Dict[date, DayHours]


def generate_shifts(config: Config) -> List[Shift]:
    """Generate all shifts for the month based on configuration."""
    
    # Get calendar days for the month
    year = config.global_config.year
    month = config.global_config.month
    num_days = calendar.monthrange(year, month)[1]
    
    # Convert holidays to set for fast lookup
    holiday_dates = {h.date for h in config.holidays}
    
    # Calculate shift start times based on duration
    shift_duration = config.global_config.shift_length_hours
    base_start_time = config.global_config.shift_start_time
    
    # Generate shift start times for 24-hour coverage
    shift_start_times = []
    if shift_duration == 12:
        # Two 12-hour shifts: 06:00-18:00 and 18:00-06:00
        shift_start_times = [
            (base_start_time, "DAY"),
            ((datetime.combine(date.today(), base_start_time) + timedelta(hours=12)).time(), "NIGHT")
        ]
    elif shift_duration == 8:
        # Three 8-hour shifts: 06:00-14:00, 14:00-22:00, 22:00-06:00
        base_dt = datetime.combine(date.today(), base_start_time)
        shift_start_times = [
            (base_start_time, "DAY"),
            ((base_dt + timedelta(hours=8)).time(), "DAY"),
            ((base_dt + timedelta(hours=16)).time(), "NIGHT")
        ]
    else:
        # Fallback: assume 24/duration shifts
        shifts_per_day = 24 // shift_duration
        base_dt = datetime.combine(date.today(), base_start_time)
        for i in range(shifts_per_day):
            start_time = (base_dt + timedelta(hours=i * shift_duration)).time()
            shift_type = "NIGHT" if start_time >= config.global_config.night_start or start_time < config.global_config.day_start else "DAY"
            shift_start_times.append((start_time, shift_type))
    
    shifts = []
    
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        is_sunday = current_date.weekday() == 6  # Monday is 0, Sunday is 6
        is_holiday = current_date in holiday_dates
        
        for post in config.posts:
            # Generate all shifts for this post and day
            for start_time, shift_type in shift_start_times:
                # Check if post allows this shift type
                if ((shift_type == "DAY" and hasattr(post, 'allow_day_shift') and post.allow_day_shift) or
                    (shift_type == "NIGHT" and hasattr(post, 'allow_night_shift') and post.allow_night_shift) or
                    (not hasattr(post, 'allow_day_shift') and not hasattr(post, 'allow_night_shift'))):
                    
                    shift = create_shift(
                        post_id=post.post_id,
                        shift_date=current_date,
                        start_time=start_time,
                        duration_hours=shift_duration,
                        is_sunday=is_sunday,
                        is_holiday=is_holiday,
                        shift_type=shift_type,
                        config=config
                    )
                    shifts.append(shift)
    
    return shifts


def calculate_hours_by_day(shift_start: datetime, shift_end: datetime, 
                          day_start: time, night_start: time, 
                          holiday_dates: Set[date]) -> Dict[date, DayHours]:
    """
    Calculate how many hours are worked on each day for a shift that might span multiple days.
    
    Args:
        shift_start: Start datetime of the shift
        shift_end: End datetime of the shift  
        day_start: Time when day period starts (e.g., 06:00)
        night_start: Time when night period starts (e.g., 21:00)
        holiday_dates: Set of holiday dates
        
    Returns:
        Dictionary mapping each date to DayHours worked on that date
    """
    hours_by_day = {}
    current_time = shift_start
    
    while current_time < shift_end:
        current_date = current_time.date()
        
        # Find end of current day for this shift (either end of shift or midnight)
        day_end = min(shift_end, datetime.combine(current_date + timedelta(days=1), time(0, 0)))
        
        # Calculate total hours worked on this date
        total_hours_this_day = (day_end - current_time).total_seconds() / 3600
        
        if total_hours_this_day > 0:
            # Calculate day vs night hours for this date
            day_hours, night_hours = _split_day_night_hours(
                current_time, day_end, current_date, day_start, night_start
            )
            
            # Check if this date is Sunday or holiday
            is_sunday = current_date.weekday() == 6
            is_holiday = current_date in holiday_dates
            
            hours_by_day[current_date] = DayHours(
                date=current_date,
                total_hours=total_hours_this_day,
                day_hours=day_hours,
                night_hours=night_hours,
                is_sunday=is_sunday,
                is_holiday=is_holiday
            )
        
        # Move to next day
        current_time = day_end
    
    return hours_by_day


def _split_day_night_hours(period_start: datetime, period_end: datetime, 
                          work_date: date, day_start: time, night_start: time) -> tuple[float, float]:
    """
    Split hours worked in a period into day hours and night hours.
    
    Day period: day_start (06:00) to night_start (21:00) 
    Night period: night_start (21:00) to day_start+1day (06:00 next day)
    """
    day_hours = 0.0
    night_hours = 0.0
    
    # Define day and night periods for this date
    day_period_start = datetime.combine(work_date, day_start)
    day_period_end = datetime.combine(work_date, night_start)
    
    # Night period spans two parts: evening of work_date and early morning of work_date
    night_evening_start = datetime.combine(work_date, night_start)
    night_evening_end = datetime.combine(work_date + timedelta(days=1), time(0, 0))
    night_morning_start = datetime.combine(work_date, time(0, 0))
    night_morning_end = datetime.combine(work_date, day_start)
    
    # Calculate overlap with day period (06:00-21:00)
    day_overlap_start = max(period_start, day_period_start)
    day_overlap_end = min(period_end, day_period_end)
    if day_overlap_end > day_overlap_start:
        day_hours += (day_overlap_end - day_overlap_start).total_seconds() / 3600
    
    # Calculate overlap with night period - evening part (21:00-24:00)
    night_evening_overlap_start = max(period_start, night_evening_start)
    night_evening_overlap_end = min(period_end, night_evening_end)
    if night_evening_overlap_end > night_evening_overlap_start:
        night_hours += (night_evening_overlap_end - night_evening_overlap_start).total_seconds() / 3600
    
    # Calculate overlap with night period - morning part (00:00-06:00)
    night_morning_overlap_start = max(period_start, night_morning_start)
    night_morning_overlap_end = min(period_end, night_morning_end)
    if night_morning_overlap_end > night_morning_overlap_start:
        night_hours += (night_morning_overlap_end - night_morning_overlap_start).total_seconds() / 3600
    
    return day_hours, night_hours


def create_shift(post_id: str, shift_date: date, start_time: time, 
                duration_hours: int, is_sunday: bool, is_holiday: bool, 
                shift_type: str, config: Config) -> Shift:
    """Create a single shift object with hours properly distributed by day."""
    
    # Calculate start and end times
    start_datetime = datetime.combine(shift_date, start_time)
    end_datetime = start_datetime + timedelta(hours=duration_hours)
    end_time = end_datetime.time()
    
    # Determine if shift is night (based on start time)
    is_night = shift_type == "NIGHT"
    
    # Convert holidays to set for fast lookup
    holiday_dates = {h.date for h in config.holidays}
    
    # Calculate hours by day
    hours_by_day = calculate_hours_by_day(
        start_datetime, end_datetime, 
        config.global_config.day_start, 
        config.global_config.night_start,
        holiday_dates
    )
    
    # Determine if shift touches Sunday (any day worked is Sunday)
    shift_touches_sunday = any(day_hours.is_sunday for day_hours in hours_by_day.values())
    
    # Determine if shift touches holiday (any day worked is holiday)
    shift_touches_holiday = any(day_hours.is_holiday for day_hours in hours_by_day.values())
    
    # Create unique shift ID
    shift_id = f"{post_id}_{shift_date.strftime('%Y%m%d')}_{shift_type}"
    
    return Shift(
        post_id=post_id,
        date=shift_date,
        start_time=start_time,
        end_time=end_time,
        duration_hours=duration_hours,
        is_night=is_night,
        is_sunday=shift_touches_sunday,
        is_holiday=shift_touches_holiday,
        shift_id=shift_id,
        hours_by_day=hours_by_day
    )


def calculate_night_hours(shift: Shift, night_start: time, day_start: time) -> float:
    """Calculate how many hours of a shift fall in the night window (21:00-06:00)."""
    
    # Create datetime objects for the shift
    shift_start = datetime.combine(shift.date, shift.start_time)
    shift_end = shift_start + timedelta(hours=shift.duration_hours)
    
    # Handle shifts that cross midnight
    if shift_end.date() > shift.date:
        # Night window for the first day (21:00 to midnight)
        night_start_day1 = datetime.combine(shift.date, night_start)
        midnight_day1 = datetime.combine(shift.date + timedelta(days=1), time(0, 0))
        
        # Night window for the second day (midnight to 06:00)
        midnight_day2 = datetime.combine(shift_end.date(), time(0, 0))
        day_start_day2 = datetime.combine(shift_end.date(), day_start)
        
        # Calculate overlap with first night window
        overlap1_start = max(shift_start, night_start_day1)
        overlap1_end = min(shift_end, midnight_day1)
        overlap1_hours = max(0, (overlap1_end - overlap1_start).total_seconds() / 3600)
        
        # Calculate overlap with second night window
        overlap2_start = max(shift_start, midnight_day2)
        overlap2_end = min(shift_end, day_start_day2)
        overlap2_hours = max(0, (overlap2_end - overlap2_start).total_seconds() / 3600)
        
        return overlap1_hours + overlap2_hours
    
    else:
        # Shift doesn't cross midnight
        night_start_datetime = datetime.combine(shift.date, night_start)
        day_start_next = datetime.combine(shift.date + timedelta(days=1), day_start)
        
        # Check if shift overlaps with night window
        overlap_start = max(shift_start, night_start_datetime)
        overlap_end = min(shift_end, day_start_next)
        
        if overlap_end <= overlap_start:
            return 0.0
        
        return (overlap_end - overlap_start).total_seconds() / 3600


def get_shifts_with_conflicts(shifts: List[Shift], min_rest_hours: float = 0) -> List[tuple]:
    """Get pairs of shifts that conflict due to consecutive shift rule.
    
    Simplified rule: An employee cannot work two consecutive shifts:
    1. Overlapping shifts (same time)
    2. Back-to-back shifts (one ends when the other starts)
    
    min_rest_hours parameter is ignored (kept for compatibility).
    """
    
    conflicts = []
    
    for i, shift1 in enumerate(shifts):
        for j, shift2 in enumerate(shifts[i+1:], i+1):
            if shifts_conflict(shift1, shift2):
                conflicts.append((shift1.shift_id, shift2.shift_id))
    
    return conflicts


def shifts_conflict(shift1: Shift, shift2: Shift, min_rest_hours: float = 0) -> bool:
    """Check if two shifts conflict - simplified rule: no consecutive shifts.
    
    An employee cannot work two consecutive shifts, defined as:
    1. Overlapping shifts (same time)
    2. Back-to-back shifts (one ends when the other starts)
    
    min_rest_hours parameter is ignored (kept for compatibility).
    """
    
    # Create datetime objects
    start1 = datetime.combine(shift1.date, shift1.start_time)
    end1 = start1 + timedelta(hours=shift1.duration_hours)
    
    start2 = datetime.combine(shift2.date, shift2.start_time)
    end2 = start2 + timedelta(hours=shift2.duration_hours)
    
    # Rule 1: Check if shifts overlap in time (same employee can't be in two places)
    if not (end1 <= start2 or end2 <= start1):
        return True
    
    # Rule 2: Check if shifts are consecutive (back-to-back)
    # Consecutive means one ends exactly when the other starts
    if end1 == start2 or end2 == start1:
        return True
    
    # Otherwise, shifts don't conflict
    return False