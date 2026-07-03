# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    VECLIB_MAXIMUM_THREADS=2 \
    NUMEXPR_NUM_THREADS=2

# Install system dependencies for OpenCV and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install CPU version of PyTorch and torchvision to keep the image slim
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.0.0" \
    "torchvision>=0.15.0"

# Copy only the requirements first to leverage Docker cache
COPY requirements.txt /app/

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Create artifacts subdirectories and ensure they are writable by Hugging Face's non-root user (UID 1000)
RUN mkdir -p /app/artifacts/logs /app/artifacts/uploads /app/artifacts/checkpoints && \
    chmod -R 777 /app

# Expose the default port for Hugging Face Spaces (7860)
EXPOSE 7860

# Command to run the dashboard
CMD ["python", "scripts/run.py", "--mode", "dashboard", "--host", "0.0.0.0", "--port", "7860"]
