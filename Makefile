SHELL := /bin/bash
.DEFAULT_GOAL := help

# -------------------------------------------------------------------
# Local dev
# -------------------------------------------------------------------
.PHONY: up down logs

up: ## Start API + inference + UI
	APP_VERSION=$$(cat VERSION 2>/dev/null || echo "dev") docker compose up --build -d api inference ui

down: ## Stop all services
	docker compose down

logs: ## Tail logs
	docker compose logs -f

# -------------------------------------------------------------------
# Pipeline jobs (one-shot)
# -------------------------------------------------------------------
.PHONY: acquire train

acquire: ## Run acquisition pipeline
	docker compose --profile pipeline run --rm acquisition python cli.py run --source-dir /app/data

train: ## Run training pipeline
	docker compose --profile pipeline run --rm training python cli.py run

# -------------------------------------------------------------------
# Individual services
# -------------------------------------------------------------------
.PHONY: api inference ui

api: ## Start API only
	docker compose up --build api

inference: ## Start inference only
	docker compose up --build inference

ui: ## Start UI only
	docker compose up --build ui

# -------------------------------------------------------------------
# Docker images (CI)
# -------------------------------------------------------------------
REGISTRY ?= us-central1-docker.pkg.dev
PROJECT  ?= support-copilot
REPO     ?= images
TAG      ?= latest

.PHONY: build-all push-all

VERSION ?= $(shell cat VERSION 2>/dev/null || echo "dev")

build-all: ## Build all Docker images
	docker build -t $(REGISTRY)/$(PROJECT)/$(REPO)/acquisition:$(TAG) ./acquisition
	docker build -t $(REGISTRY)/$(PROJECT)/$(REPO)/training:$(TAG)    ./training
	docker build --build-arg APP_VERSION=$(VERSION) -t $(REGISTRY)/$(PROJECT)/$(REPO)/inference:$(TAG)   ./inference
	docker build --build-arg APP_VERSION=$(VERSION) -t $(REGISTRY)/$(PROJECT)/$(REPO)/api:$(TAG)         ./api
	docker build --build-arg NEXT_PUBLIC_APP_VERSION=$(VERSION) -t $(REGISTRY)/$(PROJECT)/$(REPO)/ui:$(TAG)          ./ui

push-all: ## Push all Docker images
	docker push $(REGISTRY)/$(PROJECT)/$(REPO)/acquisition:$(TAG)
	docker push $(REGISTRY)/$(PROJECT)/$(REPO)/training:$(TAG)
	docker push $(REGISTRY)/$(PROJECT)/$(REPO)/inference:$(TAG)
	docker push $(REGISTRY)/$(PROJECT)/$(REPO)/api:$(TAG)
	docker push $(REGISTRY)/$(PROJECT)/$(REPO)/ui:$(TAG)

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------
.PHONY: lint test help

lint: ## Lint Python code
	cd api && uv run ruff check .
	cd inference && uv run ruff check .
	cd acquisition && uv run ruff check .
	cd training && uv run ruff check .

test: ## Run API tests
	cd api && uv run pytest tests/ -v

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
