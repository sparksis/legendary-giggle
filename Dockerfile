# Use an official lightweight Python image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application script and configuration file
COPY sync_recordings.py .
COPY config.ini .

# Set the command to run the script when the container starts
# Note: The user will need to mount volumes for `recordings` and `state.json`
# as described in the README.md to ensure data persistence.
CMD ["python", "sync_recordings.py"]
