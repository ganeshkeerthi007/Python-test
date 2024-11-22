# Start with a lightweight Python image
FROM python:3.11-slim
 
# Copy only requirements file to leverage Docker cache if dependencies don’t change
COPY requirements.txt .
 
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy the rest of the application code into the container
COPY . .
 
# Set the default command to run your main application file
CMD ["python", "main.py"]
 