# Stage 1: Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files to disc
# and to ensure output is sent straight to the terminal (good for logs)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# The data file (elsst_current.jsonld) is expected to be mounted into the container at runtime.
# It is NOT included in the image to keep the image size small and portable.

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application using Gunicorn for production
#CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "server:app"]
ENTRYPOINT ["python", "server.py"]
