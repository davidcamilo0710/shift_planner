# 24/7 Shift Scheduler for Security Posts

A comprehensive optimization system for scheduling security guard shifts with automatic cost minimization and constraint satisfaction. Now available as both a command-line tool and REST API!

## 🚀 New: REST API Deployment

This system is now available as a FastAPI REST API ready for deployment on DigitalOcean App Platform!

### API Features
- **FastAPI Framework**: High-performance async API with automatic OpenAPI documentation
- **File Processing**: Upload Excel configuration files and get optimized schedules back
- **Production Ready**: Configured with Gunicorn, health checks, and proper error handling
- **Cloud Deployment**: One-click deployment to DigitalOcean App Platform
- **Interactive Documentation**: Built-in Swagger UI at `/docs`

### Quick API Start

#### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API locally
python api.py
# or
uvicorn api:app --reload

# Access the API at http://localhost:8000
# View docs at http://localhost:8000/docs
```

#### Using the API
```bash
# Process a schedule via API
curl -X POST "http://localhost:8000/process" \
     -F "config_file=@config/optimizer_config.xlsx" \
     -F "strategy=lexicographic" \
     -F "log_level=INFO" \
     -F "generate_validation=false" \
     -o optimized_schedule.xlsx

# Check API health
curl http://localhost:8000/health

# View usage guide
curl http://localhost:8000/docs/usage
```

#### Deploy to DigitalOcean

1. **Push to GitHub**: Commit all files to your repository
2. **Create App**: Go to DigitalOcean App Platform → Create App → Import from GitHub
3. **Auto-Deploy**: The `.do/app.yaml` configuration handles everything automatically
4. **Use API**: Your API will be available at `https://your-app-name.ondigitalocean.app`

### API Endpoints

- `POST /process` - Upload config file and get optimized schedule
- `GET /health` - Health check for monitoring
- `GET /docs` - Interactive API documentation
- `GET /docs/usage` - API usage instructions
- `GET /` - API information

## Original Features

### Core Optimization
- **Lexicographic Priority**: Minimizes costs in order of importance
  1. Overtime (HE) - highest priority
  2. Holiday surcharge (RF) - medium priority  
  3. Night surcharge (RN) - lowest priority
- **Alternative Weighted Optimization**: Custom weights for different cost components
- **Complete Coverage**: Ensures 24/7 coverage for all security posts
- **Constraint Satisfaction**: Respects rest periods, employee limits, and business rules

### Business Rules Implementation
- **Rest Periods**: Configurable minimum hours between shifts (default 12h)
- **Employee Types**:
  - Fixed employees: assigned to specific posts (minimum 3 per post)
  - Comodines: can rotate between posts (configurable limit)
- **Holiday Surcharge Rules**: Special handling of Sunday work limits
- **Night Hours**: Automatic calculation based on 21:00-06:00 window

### Input/Output
- **Excel Configuration**: Complete setup via `optimizer_config.xlsx`
- **Excel Results**: Detailed assignments, summaries, and KPIs
- **Verification**: Built-in solution validation and reporting

## Command Line Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Your Scenario
Edit `config/optimizer_config.xlsx` with your:
- Posts and coverage requirements
- Employee details (fixed/comodin assignments)
- Holiday dates
- Optimization parameters

### 3. Run Optimization
```bash
python run_optimizer.py --config config/optimizer_config.xlsx --output output/results.xlsx
```

### 4. View Results
The system generates:
- `Asignacion`: Daily shift assignments
- `Resumen_Empleado`: Hours and costs per employee
- `Resumen_Puesto`: Costs per post
- `KPIs`: Overall metrics and totals

## Configuration

### Global Parameters
```
Year/Month: Planning period
Shift Times: Day (06:00-18:00), Night (18:00-06:00)
Surcharge Rates: RN=35%, RF=80%, HE=125%
Constraints: Min rest=12h, Sunday threshold=2, Min fixed=3
```

### Employee Types
- **FIJO**: Assigned to one specific post
- **COMODIN**: Can work multiple posts (up to MaxPostsPerComodin)

### Optimization Strategies
- **Lexicographic**: Minimizes objectives in strict priority order
- **Weighted**: Single objective with configurable weights

## Advanced Usage

### Custom Optimization Strategy
```bash
python run_optimizer.py --strategy weighted --log-level DEBUG
```

### Generate Validation Report
```bash
python run_optimizer.py --validate
```

### Run Tests
```bash
python tests/test_basic_scenario.py
```

## Project Structure
```
planificador-turnos/
├── api.py                   # FastAPI REST API server
├── gunicorn_config.py       # Production server configuration
├── requirements.txt         # All dependencies (API + original)
├── .do/
│   └── app.yaml            # DigitalOcean deployment config
├── processing/
│   ├── __init__.py         
│   └── processor.py        # API wrapper for optimization logic
├── src/                    # Original optimization system
│   ├── config_loader.py    # Excel configuration reader
│   ├── shift_generator.py  # Calendar and shift creation
│   ├── optimizer.py        # CP-SAT optimization model
│   ├── result_exporter.py  # Excel results writer
│   ├── verifier.py         # Solution validation
│   └── main.py             # Original CLI logic
├── config/
│   └── optimizer_config.xlsx # Configuration template
├── output/                 # Results directory
├── tests/
│   └── test_basic_scenario.py # Basic functionality test
└── run_optimizer.py       # Original CLI runner script
```

## Example Results

For a typical scenario (1 post, 31 days, 4 employees):
- **Total Cost**: ~$8,500,000 COP/month
- **Overtime Hours**: Minimized through optimal comodin usage
- **Holiday Coverage**: Automatic compliance with Sunday rules
- **Solve Time**: < 10 seconds for monthly schedules

## Mathematical Model

### Decision Variables
- `x[emp, shift]`: Binary assignment variables
- `active[emp]`: Employee utilization variables  
- `sunday_worked[emp, date]`: Sunday tracking
- `excess_sundays[emp]`: Holiday surcharge triggers

### Key Constraints
1. **Coverage**: Each shift assigned to exactly one employee
2. **Rest Periods**: Minimum time between consecutive shifts
3. **Employee Rules**: Fixed/comodin assignment restrictions
4. **Capacity**: Post limits for comodines

### Objective Function
**Lexicographic**: MIN(HE_total) → MIN(RF_violations) → MIN(RN_total)
**Weighted**: MIN(w_HE×HE + w_RF×RF + w_RN×RN + w_BASE×Salaries)

## Validation

The system includes comprehensive validation:
- Coverage verification (all shifts assigned)
- Constraint checking (rest periods, employee rules)
- Calculation accuracy (hours, costs, surcharges)
- Business rule compliance (minimum fixed per post)

## Troubleshooting

### Common Issues
1. **Infeasible Solution**: Check minimum fixed employees per post
2. **High Overtime**: Consider adding comodines or adjusting constraints
3. **Import Errors**: Verify Python path and dependencies

### Debug Mode
```bash
python run_optimizer.py --log-level DEBUG --validate
```

## Contributing

1. Run tests before submitting changes
2. Follow existing code style and documentation
3. Validate with multiple scenarios
4. Update README for new features

## License

This system is designed for SERVAGRO shift scheduling optimization.