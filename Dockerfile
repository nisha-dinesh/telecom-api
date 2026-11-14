# Dockerfile: the recipe for the app's container.
FROM python:3.13-slim

# No .pyc files, and print logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /code

# Copy requirements first: Docker re-uses this slow step if they did not change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY seed.py .

# Run as a normal user, not root (safer if the app is ever hacked).
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]