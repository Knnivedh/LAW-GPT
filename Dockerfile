# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies
# build-essential for compiling some python packages
# git for installing from git
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
# We use a specific sentence-transformers version to ensure compatibility
# numpy<2 is often required for older libs
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir supabase numpy<2

# Copy the rest of the application
COPY . .

# Create a user to run the app (security best practice for HF Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH

# Change ownership of app directory to user
USER root
RUN chown -R user:user /app
USER user

# Expose the port Azure App Service expects
EXPOSE 8000

# Start the production API server using Gunicorn + Uvicorn workers
# --timeout 600 allows the RAG system enough time to warm up on cold start
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "600", "--graceful-timeout", "120", "main:app"]
