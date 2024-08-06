# Use the official Python image from the Docker Hub
FROM minizinc/minizinc:latest

# Set the working directory in the container
WORKDIR /src

# Copy all files into the container at /src
COPY . .

# Installing python and required dependencies
RUN apt-get update \
  && apt-get install -y python3 \
  && apt-get install -y python3-pip \
  && apt-get install -y libffi-dev 
# Install required libraries
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

# Define the command to run the application
# CMD ["python", "your_script.py"]
