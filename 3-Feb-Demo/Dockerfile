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

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source files and entrypoint
COPY controller.py .
COPY collector.py .
COPY entrypoint.sh .

# Copy the dump1090 binary (from local file "dump1090") and make it executable
COPY dump1090 /usr/local/bin/dump1090
RUN chmod +x /usr/local/bin/dump1090
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
