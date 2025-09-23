FROM python:3.12-slim

WORKDIR /app

COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt

COPY . .

EXPOSE 5001

CMD ["gunicorn", "test_app:app", "--bind", "0.0.0.0:5001"]