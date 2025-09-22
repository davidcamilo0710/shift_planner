from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List, Set
import calendar

try:
    from .config_loader import Config
except ImportError:
    from config_loader import Config


@dataclass
class Shift:
    post_id: str
    date: date
    start_time: time
    end_time: time
    duration_hours: int
    is_night: bool
    is_sunday: bool
    is_holiday: bool
    shift_id: str


def generate_shifts(config: Config) -> List[Shift]:
    """Generate all shifts for the month based on configuration."""
    
    # Get calendar days for the month
    year = config.global_config.year
    month = config.global_config.month
    num_days = calendar.monthrange(year, month)[1]
    
    # Convert holidays to set for fast lookup
    holiday_dates = {h.date for h in config.holidays}
    
    shifts = []
    
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        is_sunday = current_date.weekday() == 6  # Monday is 0, Sunday is 6
        is_holiday = current_date in holiday_dates
        
        for post in config.posts:
            # Generate day shift if allowed
            if post.allow_day_shift:
                day_shift = create_shift(
                    post_id=post.post_id,
                    shift_date=current_date,
                    start_time=config.global_config.day_shift_start,
                    duration_hours=config.global_config.shift_length_hours,
                    is_sunday=is_sunday,
                    is_holiday=is_holiday,
                    shift_type="DAY"
                )
                shifts.append(day_shift)
            
            # Generate night shift if allowed
            if post.allow_night_shift:
                night_shift = create_shift(
                    post_id=post.post_id,
                    shift_date=current_date,
                    start_time=config.global_config.night_shift_start,
                    duration_hours=config.global_config.shift_length_hours,
                    is_sunday=is_sunday,
                    is_holiday=is_holiday,
                    shift_type="NIGHT"
                )
                shifts.append(night_shift)
    
    return shifts


def create_shift(post_id: str, shift_date: date, start_time: time, 
                duration_hours: int, is_sunday: bool, is_holiday: bool, 
                shift_type: str) -> Shift:
    """Create a single shift object."""
    
    # Calculate end time
    start_datetime = datetime.combine(shift_date, start_time)
    end_datetime = start_datetime + timedelta(hours=duration_hours)
    end_time = end_datetime.time()
    
    # Determine if shift is night (based on start time)
    is_night = shift_type == "NIGHT"
    
    # Check if shift touches Sunday (either starts on Sunday OR ends on Sunday)
    shift_touches_sunday = is_sunday or end_datetime.date().weekday() == 6
    
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
        is_holiday=is_holiday,
        shift_id=shift_id
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


def get_shifts_with_conflicts(shifts: List[Shift], min_rest_hours: float) -> List[tuple]:
    """Get pairs of shifts that violate minimum rest time."""
    
    conflicts = []
    
    for i, shift1 in enumerate(shifts):
        for j, shift2 in enumerate(shifts[i+1:], i+1):
            if shifts_conflict(shift1, shift2, min_rest_hours):
                conflicts.append((shift1.shift_id, shift2.shift_id))
    
    return conflicts


def shifts_conflict(shift1: Shift, shift2: Shift, min_rest_hours: float) -> bool:
    """Check if two shifts conflict due to minimum rest requirements."""
    
    # Create datetime objects
    start1 = datetime.combine(shift1.date, shift1.start_time)
    end1 = start1 + timedelta(hours=shift1.duration_hours)
    
    start2 = datetime.combine(shift2.date, shift2.start_time)
    end2 = start2 + timedelta(hours=shift2.duration_hours)
    
    # Check if shifts overlap in time
    if not (end1 <= start2 or end2 <= start1):
        return True
    
    # Check minimum rest time
    if end1 <= start2:
        rest_time = (start2 - end1).total_seconds() / 3600
        if rest_time < min_rest_hours:
            return True
    
    if end2 <= start1:
        rest_time = (start1 - end2).total_seconds() / 3600
        if rest_time < min_rest_hours:
            return True
    
    return False