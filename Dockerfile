FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 EOV_DATABASE=/data/eov.sqlite3
COPY alpha/requirements.txt /app/alpha/requirements.txt
RUN pip install --no-cache-dir -r /app/alpha/requirements.txt
COPY alpha /app/alpha
COPY docs/play /app/docs/play
RUN mkdir /data
EXPOSE 8000
# One worker is required: live positions and socket subscriptions are process-local.
CMD ["sh", "-c", "exec uvicorn alpha.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --ws-max-size 8192"]
