#!/bin/bash

# Set default port if PORT is not set
if [ -z "$PORT" ]; then
    export PORT=5001
fi

echo "Starting application on port $PORT"

# Start the application
gunicorn test_app:app --bind 0.0.0.0:$PORT
