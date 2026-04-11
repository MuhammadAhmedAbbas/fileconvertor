# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/app/uploads \
    OUTPUT_DIR=/app/outputs \
    PORT=5000

# Install system dependencies (LibreOffice for Word→PDF, fonts, image support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libreoffice \
    fonts-liberation \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Create uploads and outputs directories
RUN mkdir -p /app/uploads /app/outputs && chmod 777 /app/uploads /app/outputs

# Expose the port the app runs on
EXPOSE $PORT

# Run the application – Railway injects $PORT at runtime
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2
