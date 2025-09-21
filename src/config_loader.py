from dataclasses import dataclass
from datetime import datetime, date, time
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path


@dataclass
class GlobalConfig:
    year: int
    month: int
    day_start: time  # End of night hours (HH:MM)
    night_start: time  # Start of night hours (HH:MM)
    rn_pct: float  # Night surcharge percentage
    rf_pct: float  # Holiday surcharge percentage
    he_pct: float  # Overtime percentage
    hours_base_month: float  # Base hours for salary/hour calculation
    hours_per_week: float  # Hours/week for overtime calculation
    min_fixed_per_post: int  # Minimum fixed employees per post
    shift_length_hours: int  # Shift duration
    day_shift_start: time  # Day shift start time
    night_shift_start: time  # Night shift start time
    min_rest_hours: float  # Minimum rest hours between shifts
    sunday_threshold: int  # Sunday threshold for holiday surcharge
    max_posts_per_comodin: int  # Maximum posts per comodin
    use_lexicographic: bool  # Use lexicographic priority
    w_he: float  # Overtime weight
    w_rf: float  # Holiday weight
    w_rn: float  # Night weight
    w_base: float  # Base salary weight


@dataclass
class Holiday:
    date: date
    description: str


@dataclass
class Post:
    post_id: str
    nombre: str
    required_coverage: int
    allow_day_shift: bool
    allow_night_shift: bool


@dataclass
class Employee:
    emp_id: str
    tipo: str  # FIJO or COMODIN
    asignado_post_id: Optional[str]
    empresa: str
    cargo: str
    cliente: str
    salario_contrato: float
    disponible_desde: date
    disponible_hasta: date
    max_posts_if_comodin: int


@dataclass
class Config:
    global_config: GlobalConfig
    holidays: List[Holiday]
    posts: List[Post]
    employees: List[Employee]


def parse_time(time_obj) -> time:
    """Parse time from various formats."""
    if isinstance(time_obj, str):
        return datetime.strptime(time_obj, "%H:%M").time()
    elif isinstance(time_obj, time):
        return time_obj
    elif isinstance(time_obj, datetime):
        return time_obj.time()
    else:
        raise ValueError(f"Cannot parse time: {time_obj}")


def parse_date(date_obj) -> date:
    """Parse date from various formats."""
    if isinstance(date_obj, str):
        return datetime.strptime(date_obj, "%Y-%m-%d").date()
    elif isinstance(date_obj, datetime):
        return date_obj.date()
    elif isinstance(date_obj, date):
        return date_obj
    else:
        raise ValueError(f"Cannot parse date: {date_obj}")


def load_config(xlsx_path: Path) -> Config:
    """Load configuration from Excel file."""
    
    # Load Global sheet
    global_df = pd.read_excel(xlsx_path, sheet_name='Global')
    global_data = {}
    for _, row in global_df.iterrows():
        field = row['Campo']
        value = row['Valor']
        global_data[field] = value
    
    global_config = GlobalConfig(
        year=int(global_data['Year']),
        month=int(global_data['Month']),
        day_start=parse_time(global_data['DayStart']),
        night_start=parse_time(global_data['NightStart']),
        rn_pct=float(global_data['RN_pct']),
        rf_pct=float(global_data['RF_pct']),
        he_pct=float(global_data['HE_pct']),
        hours_base_month=float(global_data['HoursBaseMonth']),
        hours_per_week=float(global_data['HoursPerWeek']),
        min_fixed_per_post=int(global_data['MinFixedPerPost']),
        shift_length_hours=int(global_data['ShiftLengthHours']),
        day_shift_start=parse_time(global_data['DayShiftStart']),
        night_shift_start=parse_time(global_data['NightShiftStart']),
        min_rest_hours=float(global_data['MinRestHours']),
        sunday_threshold=int(global_data['SundayThreshold']),
        max_posts_per_comodin=int(global_data['MaxPostsPerComodin']),
        use_lexicographic=bool(global_data['UseLexicographic']),
        w_he=float(global_data['w_HE']),
        w_rf=float(global_data['w_RF']),
        w_rn=float(global_data['w_RN']),
        w_base=float(global_data['w_BASE'])
    )
    
    # Load Holidays sheet
    holidays_df = pd.read_excel(xlsx_path, sheet_name='Festivos')
    holidays = []
    for _, row in holidays_df.iterrows():
        holidays.append(Holiday(
            date=parse_date(row['Date']),
            description=row['Description']
        ))
    
    # Load Posts sheet
    posts_df = pd.read_excel(xlsx_path, sheet_name='Puestos')
    posts = []
    for _, row in posts_df.iterrows():
        posts.append(Post(
            post_id=row['PostID'],
            nombre=row['Nombre'],
            required_coverage=int(row['RequiredCoverage']),
            allow_day_shift=bool(row['AllowDayShift']),
            allow_night_shift=bool(row['AllowNightShift'])
        ))
    
    # Load Employees sheet  
    employees_df = pd.read_excel(xlsx_path, sheet_name='Empleados')
    employees = []
    for _, row in employees_df.iterrows():
        # Handle missing values
        max_posts = row['MaxPostsIfComodin'] if pd.notna(row['MaxPostsIfComodin']) else 4
        
        employees.append(Employee(
            emp_id=row['EmpID'],
            tipo=row['Tipo'],
            asignado_post_id=row['AsignadoPostID'] if pd.notna(row['AsignadoPostID']) else None,
            empresa=row['Empresa'] if pd.notna(row['Empresa']) else '',
            cargo=row['Cargo'] if pd.notna(row['Cargo']) else '',
            cliente=row['Cliente'] if pd.notna(row['Cliente']) else '',
            salario_contrato=float(row['SalarioContrato']),
            disponible_desde=parse_date(row['DisponibleDesde']),
            disponible_hasta=parse_date(row['DisponibleHasta']),
            max_posts_if_comodin=int(max_posts)
        ))
    
    return Config(
        global_config=global_config,
        holidays=holidays,
        posts=posts,
        employees=employees
    )