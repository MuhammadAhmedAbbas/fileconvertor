# Use full Python image (not slim) — avoids ALL missing native library issues
# slim strips libgeos, libxml2, libxslt etc. needed by pdf2docx/shapely/lxml
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/app/uploads \
    OUTPUT_DIR=/app/outputs \
    PORT=5000

# Install system dependencies
# - libgl1, libglib2.0-0: opencv-python-headless
# - libsm6, libxext6, libxrender1: OpenCV GUI deps (headless still needs these)
# - libreoffice-writer + extras: Word → PDF conversion (no Java needed)
# - fonts-*: required for high-quality PDF rendering and LibreOffice
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto \
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

# Expose the default port
EXPOSE 5000

# Run the application
# --workers 1   : avoids OOM on Railway free tier (512MB limit)
# --preload     : imports the app ONCE in master; if it crashes, you see why
# --timeout 120 : allow slow PDF operations to complete
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --preload --timeout 120
