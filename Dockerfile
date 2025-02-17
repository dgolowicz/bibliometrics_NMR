# Use Python 3.12 as the base image
FROM python:3.12

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y libsqlite3-dev

# Upgrade pip before installing dependencies
RUN pip install --upgrade pip

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project, including data.db
COPY . .

# Expose port 8080
EXPOSE 8080

# Start the app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:server"]

