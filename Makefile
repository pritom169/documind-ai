.PHONY: help build up down migrate test lint shell

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f

migrate: ## Run Django migrations
	docker compose exec api python manage.py migrate

makemigrations: ## Create new migrations
	docker compose exec api python manage.py makemigrations

createsuperuser: ## Create a Django superuser
	docker compose exec api python manage.py createsuperuser

test: ## Run the test suite
	docker compose exec api pytest

test-local: ## Run tests locally (without Docker)
	pytest

lint: ## Run linter
	ruff check . --fix

shell: ## Open Django shell
	docker compose exec api python manage.py shell

dbshell: ## Open database shell
	docker compose exec postgres psql -U documind -d documind

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli

k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/postgres-deployment.yaml
	kubectl apply -f k8s/postgres-service.yaml
	kubectl apply -f k8s/redis-deployment.yaml
	kubectl apply -f k8s/redis-service.yaml
	kubectl apply -f k8s/qdrant-deployment.yaml
	kubectl apply -f k8s/qdrant-service.yaml
	kubectl apply -f k8s/django-deployment.yaml
	kubectl apply -f k8s/django-service.yaml
	kubectl apply -f k8s/celery-deployment.yaml
	kubectl apply -f k8s/ingress.yaml
	kubectl apply -f k8s/hpa.yaml

k8s-delete: ## Delete Kubernetes deployment
	kubectl delete namespace documind
