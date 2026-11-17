FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Single worker only: the reminder scheduler runs in-process and must
# not be duplicated across workers, or reminders would fire multiple times.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
