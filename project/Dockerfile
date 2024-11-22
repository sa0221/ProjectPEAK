FROM node:20-slim as frontend-builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libusb-1.0-0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built frontend
COPY --from=frontend-builder /app/dist ./dist

# Copy the backend code
COPY api ./api

# Copy the collector script
COPY api/collector.py .

# Expose ports for both services
EXPOSE 5000 5173

# Create a startup script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]