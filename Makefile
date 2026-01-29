.PHONY: help install dev prod test clean docker-build docker-up docker-down

# Variables
PYTHON := python3
PIP := pip3
PORT := 8000
HOST := 0.0.0.0

help: ## Show this help message
	@echo "Amazon Product Research API - Makefile"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

install: ## Install dependencies
	$(PIP) install -r requirements.txt

dev: ## Run development server
	$(PYTHON) main.py

prod: ## Run production server
	uvicorn main:app --host $(HOST) --port $(PORT) --workers 4

test: ## Run tests
	pytest -v

lint: ## Run linting checks
	flake8 api/ research_agents/ main.py --max-line-length=120

format: ## Format code with black
	black api/ research_agents/ main.py --line-length=120

docker-build: ## Build Docker image
	docker build -t amazon-research-api:latest .

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f app

clean: ## Clean up temporary files, caches, and .md files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	rm -f *.md 2>/dev/null || true
	@echo "Cleanup complete"

.DEFAULT_GOAL := help
