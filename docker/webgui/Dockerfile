# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the Python files and directories to the container
COPY ./python/ /app

# Set environment variables
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1
# Set the CCDB_HOME environment variable
ENV CCDB_HOME=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

COPY ./python/requirements.txt .
COPY ./python/ccdb/webgui/requirements-web.txt .
# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-web.txt

# Expose the port the app runs on
EXPOSE 5000

# Set the command to run the application with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "ccdbweb:app"]
