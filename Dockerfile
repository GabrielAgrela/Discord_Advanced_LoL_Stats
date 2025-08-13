FROM mcr.microsoft.com/playwright/python:v1.41.1-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add src to Python path
ENV PYTHONPATH=/app

# Change the CMD to enable debugging
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "src.bot"]
#without debugpy
#CMD ["python", "-m", "src.bot"]
