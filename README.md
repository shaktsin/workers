# Description 

The Inference Platform Workflow is a standalone, scalable component that retrieves tasks from the queue and orchestrates the creation of necessary Kubernetes objects to provision the infrastructure for the inference service.

# Build & Publish 

## Prerequisite 

You need to install the following utility locally 
- Docker

## Help

`make help`

## Build 

`make build`

## Run locally 

To be able to run locally, you need to install redis and override your local path (SRC_DB_MOUNT) in Makefile  

`make run-local`

## Push to AWS

To be able to push image to ECR public repo, create ECR repo first 
`aws ecr-public create-repository --repository-name <name> --region <region>`
Once repo, it created, update repo name and url in makefile and run the following 

`make push`
