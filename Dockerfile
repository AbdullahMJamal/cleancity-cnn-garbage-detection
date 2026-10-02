# CleanCity – production image (used by Hugging Face Spaces, works on any Docker host)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    PORT=7860

# Hugging Face Spaces runs containers as user 1000
RUN useradd -m -u 1000 app
WORKDIR /app

# tensorflow-cpu is much smaller than the full GPU build
RUN pip install --no-cache-dir tensorflow-cpu==2.21.0 flask werkzeug numpy Pillow gunicorn

COPY --chown=app:app . .
RUN mkdir -p instance static/uploads && chown -R app:app instance static/uploads
USER app

EXPOSE 7860
# 1 worker (the model is loaded once), 4 threads for concurrent requests
CMD gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT} "app:create_app()"
