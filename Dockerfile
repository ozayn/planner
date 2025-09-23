FROM python:3.12-slim

WORKDIR /app

COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt

COPY . .

# Railway will set the PORT environment variable
EXPOSE $PORT

CMD ["sh", "-c", "gunicorn test_app:app --bind 0.0.0.0:$PORT"]