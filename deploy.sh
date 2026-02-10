#!/bin/bash

# PowerLit API Deployment Script
# Supports: Docker, Railway, Render

set -e

echo "🚀 PowerLit API Deployment Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to deploy with Docker
deploy_docker() {
    echo -e "${GREEN}Deploying with Docker...${NC}"
    
    if ! command_exists docker; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        echo -e "${RED}Error: docker-compose is not installed${NC}"
        echo "Please install docker-compose first"
        exit 1
    fi
    
    echo "Building and starting containers..."
    docker-compose up --build -d
    
    echo ""
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo "API is running at: http://localhost:8000"
    echo "API Documentation: http://localhost:8000/docs"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
}

# Function to deploy to Railway
deploy_railway() {
    echo -e "${GREEN}Deploying to Railway...${NC}"
    
    if ! command_exists railway; then
        echo -e "${YELLOW}Railway CLI not found. Installing...${NC}"
        npm install -g @railway/cli
    fi
    
    if ! railway --version >/dev/null 2>&1; then
        echo -e "${RED}Error: Railway CLI installation failed${NC}"
        exit 1
    fi
    
    echo "Logging in to Railway..."
    railway login
    
    echo "Initializing project..."
    railway init
    
    echo "Deploying..."
    railway up
    
    echo ""
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    railway status
}

# Function to deploy to Render
deploy_render() {
    echo -e "${GREEN}Deploying to Render...${NC}"
    
    echo "Please follow these steps to deploy to Render:"
    echo ""
    echo "1. Push your code to GitHub/GitLab"
    echo "2. Go to https://render.com and sign up/login"
    echo "3. Click 'New +' and select 'Web Service'"
    echo "4. Connect your repository"
    echo "5. Use these settings:"
    echo "   - Name: powerlit-api"
    echo "   - Runtime: Docker"
    echo "   - Branch: main (or your default branch)"
    echo "   - Instance Type: Standard"
    echo "6. Click 'Create Web Service'"
    echo ""
    echo -e "${YELLOW}Note: Render will automatically build from your Dockerfile${NC}"
}

# Function to show manual deployment instructions
deploy_manual() {
    echo -e "${GREEN}Manual Deployment Instructions${NC}"
    echo ""
    echo "1. Requirements:"
    echo "   - Python 3.11+"
    echo "   - Tesseract OCR: sudo apt-get install tesseract-ocr"
    echo "   - Poppler: sudo apt-get install poppler-utils"
    echo ""
    echo "2. Setup:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate  # On Windows: venv\Scripts\activate"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "3. Run:"
    echo "   uvicorn main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "4. Production (with gunicorn):"
    echo "   pip install gunicorn"
    echo "   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
}

# Main menu
echo "Select deployment method:"
echo "1) Docker (recommended for local/production)"
echo "2) Railway (cloud platform)"
echo "3) Render (cloud platform)"
echo "4) Manual deployment"
echo ""

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        deploy_docker
        ;;
    2)
        deploy_railway
        ;;
    3)
        deploy_render
        ;;
    4)
        deploy_manual
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
