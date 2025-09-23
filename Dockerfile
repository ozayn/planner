# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements-railway.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-railway.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5001

# Start command - using test app for debugging
CMD gunicorn test_app:app --bind 0.0.0.0:5001

