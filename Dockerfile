# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libusb-1.0-0-dev \
    pkg-config \
    curl \
    wget \
    rtl-sdr \
    tcpdump \
    libncurses5 \
    libncursesw5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY api ./api

# Copy the dump1090 binary and make it executable
COPY dump1090-project /usr/local/bin/dump1090
RUN chmod +x /usr/local/bin/dump1090

# Expose the port
EXPOSE 8000

# Start the application
CMD ["python", "api/server.py"]
