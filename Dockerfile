FROM python:3.12-slim

WORKDIR /app

# Install deps first (separate layer. changes less often than source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=5000
EXPOSE 5000

# Non-root user: principle of least privilege
RUN adduser --disabled-password --gecos "" appuser
USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
