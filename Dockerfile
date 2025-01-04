FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Add src to Python path
ENV PYTHONPATH=/app

# Change the CMD to enable debugging
#CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m", "src.bot"]
#without debugpy
CMD ["python", "-m", "src.bot"]