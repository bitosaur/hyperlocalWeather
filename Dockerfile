FROM python:3.12-slim

# Non-root user for security
RUN useradd --create-home appuser

WORKDIR /home/appuser/app

# Install dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ .

USER appuser

EXPOSE 5000

# gunicorn with a single worker — this app is intentionally low-traffic
# (one Kindle polling every REFRESH_INTERVAL seconds).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "30", "app:app"]
