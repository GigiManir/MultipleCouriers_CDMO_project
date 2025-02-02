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
  && apt-get install -y libffi-dev \
  && apt-get install -y git 
# Install required libraries
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt
RUN git clone 'https://github.com/GigiManir/gurobi_solver.git'
RUN mv gurobi_solver/gurobi11.0.3_linux64/ .
RUN rm -r gurobi_solver

# Define the command to run the application
ENV GUROBI_HOME="/src/gurobi11.0.3_linux64/gurobi1103/linux64"
ENV PATH="/src/gurobi11.0.3_linux64/gurobi1103/linux64/bin:${PATH}"
ENV LD_LIBRARY_PATH="/src/gurobi11.0.3_linux64/gurobi1103/linux64/lib"
ENV GRB_LICENSE_FILE="/src/gurobi.lic"
ENV GUROBI_VERSION="11.0.3"

# RUN python3 run_all.py

# CMD ["python3", "run_all.py"]