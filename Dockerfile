# Use the official Python 3.11 slim version as the base image
FROM python:3.8

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables (optional)
ENV PYTHONUNBUFFERED=1

# Expose the port that the application runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
