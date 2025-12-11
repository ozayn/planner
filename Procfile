web: python scripts/reset_railway_database.py || true && gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --timeout 300 --workers 2
