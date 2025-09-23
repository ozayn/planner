FROM python:3.12-slim

WORKDIR /app

COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt

COPY . .

# Railway will set the PORT environment variable
EXPOSE $PORT

CMD ["sh", "-c", "python railway_data_loader.py && gunicorn app:app --bind 0.0.0.0:$PORT"]