#!/bin/bash
# Universal run script for Mac/Linux

echo "Amazon Product Research API"
echo "============================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
    echo ""
    echo "⚠️  Please edit .env file and add your OpenAI API key!"
    echo ""
    read -p "Press Enter after adding your API key..."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if container is already running
if docker-compose ps | grep -q "Up"; then
    echo "Container is already running"
    echo ""
    echo "Choose an option:"
    echo "1) Restart"
    echo "2) Stop"
    echo "3) View logs"
    echo "4) Rebuild"
    read -p "Enter choice (1-4): " choice
    
    case $choice in
        1)
            echo "Restarting..."
            docker-compose restart
            ;;
        2)
            echo "Stopping..."
            docker-compose down
            exit 0
            ;;
        3)
            echo "Viewing logs (Ctrl+C to exit)..."
            docker-compose logs -f
            exit 0
            ;;
        4)
            echo "Rebuilding..."
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
            ;;
    esac
else
    echo "Starting Docker container..."
    docker-compose up -d --build
fi

echo ""
echo "✅ Application is running!"
echo ""
echo "Open: http://localhost:8000"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
