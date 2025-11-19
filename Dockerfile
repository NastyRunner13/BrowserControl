FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install browsers (The base image usually has them, but this ensures specific versions)
RUN playwright install chromium
RUN playwright install-deps

# Copy project files
COPY . .

# Create directories for logs and screenshots
RUN mkdir -p logs screenshots

# Expose the API port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]