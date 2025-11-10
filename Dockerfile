FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    requests==2.31.0 \
    cryptography==41.0.7

# Copy blockchain files
COPY blockchain.py .
COPY blockchain_service.py .
COPY crypto_utils.py .

# Copy keys directory (if exists)
COPY keys/ ./keys/

# Create directory for blockchain data
RUN mkdir -p /data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/status', timeout=5)" || exit 1

# Start blockchain service
ENTRYPOINT ["python", "blockchain_service.py"]