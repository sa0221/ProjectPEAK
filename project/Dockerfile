# Dockerfile

# Stage 1: Build the frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the frontend
RUN npm run build

# Stage 2: Set up the backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libusb-1.0-0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built frontend from the previous stage
COPY --from=frontend-builder /app/dist ./dist

# Copy the backend code
COPY api ./api

# Copy the start script
COPY start.sh .

# Make the start script executable
RUN chmod +x start.sh

# Expose the port the app runs on
EXPOSE 5000

# Start the application
CMD ["./start.sh"]