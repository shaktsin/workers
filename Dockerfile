# Use official Python 12 slim image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

RUN mkdir -p ~/.kube

# Install dependencies required for AWS CLI
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws/

# Verify AWS CLI installation
RUN aws --version

# Accept AWS credentials as build arguments
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_REGION=us-east-1

# Set environment variables inside the container
ENV AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
ENV AWS_REGION=$AWS_REGION

# Configure AWS CLI at build time
RUN aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" && \
    aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" && \
    aws configure set region "$AWS_REGION" && \
    aws configure list

# default db location 
ENV DB_URL="/mnt/md.db"
ENV REDIS_HOST=localhost

# Copy application files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default command
CMD ["celery", "--app", "main", "worker", "--loglevel=info"]