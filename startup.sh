#!/bin/bash
# Startup script for DigitalOcean
echo "Starting Planificador de Turnos API..."
echo "PORT: $PORT"
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Start the application
exec gunicorn --bind=0.0.0.0:${PORT:-8080} --workers=2 --timeout=300 api:app