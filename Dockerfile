# Use slim Python image to keep container size small
FROM python:3.11-slim

# Install minimal system dependencies needed by OpenCV (RapidOCR dependency).
# libglib2.0-0: GLib library required by OpenCV.
# libgl1: OpenGL runtime required by OpenCV for image operations.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy and install Python dependencies first (layer caching optimization).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
