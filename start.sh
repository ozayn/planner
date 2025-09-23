#!/bin/bash

# Set default port if PORT is not set
if [ -z "$PORT" ]; then
    export PORT=5001
fi

echo "Starting application on port $PORT"

# Run data loader
python railway_data_loader.py

# Start the application
gunicorn app:app --bind 0.0.0.0:$PORT
