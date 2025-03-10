include .env

AWS_REGION=us-east-1
ECR_PUBLIC_REPO=demo-md-infra-dp
IMAGE_TAG=latest
ECR_REPO_URL=$(ECR_REPO_FQDN)/$(ECR_PUBLIC_REPO)
REDIS_PORT=6379
TRT_DB_MOUNT=/mnt


# Authenticate with AWS ECR Public
login: # login to ECR
	@echo "🔑 Logging in to AWS ECR Public..."
	@aws configure
	@aws ecr-public get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin public.ecr.aws
	@echo "✅ Logged in to AWS ECR Public."



# Build Docker Image
build: # build data plane docker image  
	@echo "🐳 Building Docker image..."
	@docker build --build-arg AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
             --build-arg AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
             --build-arg AWS_REGION="us-east-2" \
			  -t $(ECR_REPO_URL):$(IMAGE_TAG) .
	@echo "✅ Docker image built successfully."

# Run the Container Locally
run-local: # run dp locally -p $(REDIS_PORT):$(REDIS_PORT) 
	@echo "🚀 Running DP locally..."
	@docker run --rm -it -e REDIS_HOST=localhost --network host -v $(SRC_DB_MOUNT):$(TRT_DB_MOUNT):rw $(ECR_REPO_URL):$(IMAGE_TAG)
	@echo "✅ DP Started " 

# Push Docker Image to AWS ECR Public
push: login build # push data plane to ECR
	@echo "📤 Pushing Docker image to AWS ECR Public..."
	@docker push $(ECR_REPO_URL):$(IMAGE_TAG)
	@echo "✅ Docker image pushed successfully."


# Display help message
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?# "} /^[a-zA-Z_-]+:.*?# / {printf "  \033[32m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)


