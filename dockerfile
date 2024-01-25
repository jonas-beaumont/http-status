# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app/

# Copy the content of the local src directory to the working directory
COPY ./app/ .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the script
CMD ["python", "./main.py"]
