#!/bin/bash

# Set default port if PORT is not set
export PORT=${PORT:-5001}

# Run data loader
python railway_data_loader.py

# Start the application
gunicorn app:app --bind 0.0.0.0:$PORT
