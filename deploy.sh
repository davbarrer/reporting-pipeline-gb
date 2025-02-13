#!/bin/bash
echo "Pulling latest code..."
cd ~/reporting-pipeline-gb/fastapi-app || exit
git pull origin main
echo "Rebuilding Docker container..."
docker build -t fastapi-app .
docker stop fastapi-container || true
docker rm fastapi-container || true
docker run -d --name fastapi-container -p 8000:8000 fastapi-app
echo "Deployment complete!"
