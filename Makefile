.PHONY: help setup services services-down install sync sync-all run migrate makemigrations shell superuser test check deploy-check collectstatic clean module

PYTHON ?= uv run python
MANAGE ?= $(PYTHON) manage.py
COMPOSE ?= docker compose -f compose.yaml -f compose.local.yaml
LOCAL_SERVICES ?= db redis mailpit adminer
ENV_PORT := $(shell [ -f .env ] && grep '^APP_PORT=' .env | cut -d'=' -f2 | tr -d '"[:space:]')

# 2. Use terminal environment PORT, otherwise the .env PORT, otherwise fallback to 8000
ifneq ($(ENV_PORT),)
    PORT ?= $(ENV_PORT)
else
    PORT ?= 8000
endif

# `make module shop.product` passes the module name as a second goal; turn it into a no-op.
# A catch-all rule is needed because make 3.81 cannot match goals ending in `/`.
ifeq (module,$(firstword $(MAKECMDGOALS)))
    MODULE_NAME := $(word 2,$(MAKECMDGOALS))
%:
	@:
endif

help:
	@printf '%s\n' \
		'Common targets:' \
		'  make setup                   Prepare .env, dependencies, services, and database' \
		'  make services                Start local PostgreSQL, Redis, Mailpit, and Adminer' \
		'  make services-down           Stop local services' \
		'  make install                 Install dependencies' \
		'  make run                     Run development server' \
		'  make migrate                 Apply migrations' \
		'  make makemigrations          Create migrations' \
		'  make shell                   Open Django shell' \
		'  make superuser               Create admin user' \
		'  make test                    Run tests' \
		'  make check                   Run system checks' \
		'  make deploy-check            Run deployment checks' \
		'  make collectstatic           Collect static files' \
		'  make clean                   Remove Python caches' \
		'  make module NAME             Create a module or model (run without NAME for examples)'

setup:
	@[ -f .env ] || { cp .env.example .env && echo "Created .env from .env.example"; }
	@if command -v mise >/dev/null 2>&1; then mise install; else echo "mise not found; using the Python version uv selects"; fi
	uv sync --group cache
	$(MAKE) services
	$(MANAGE) migrate
	@echo "Setup complete. Run 'make superuser' to create an admin, then 'make run'."

services:
	$(COMPOSE) up -d --wait $(LOCAL_SERVICES)

services-down:
	$(COMPOSE) down

install sync:
	uv sync

sync-all:
	uv sync --all-groups

run:
	$(MANAGE) runserver $(PORT)

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

superuser:
	$(MANAGE) createsuperuser

test:
	$(MANAGE) test

check:
	$(MANAGE) check

deploy-check:
	$(MANAGE) check --deploy

collectstatic:
	$(MANAGE) collectstatic --noinput

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

module:
	@if [ -z "$(or $(MODULE_NAME),$(NAME))" ]; then \
		printf '%s\n' \
			'Usage: make module <module>[.<folder>...][.<model>]' \
			'' \
			'Separate parts with . or /. End with . or / to create a folder without a model.' \
			'Each model gets models/, admin/, and tests/ files and is exported automatically.' \
			'' \
			'Example: an online shop' \
			'  make module shop                   modules/shop/ with models/shop.py (Shop)' \
			'  make module shop.product           models/product.py (Product)' \
			'  make module shop.catalog.          models/catalog/ folder, no model' \
			'  make module shop.catalog.category  models/catalog/category.py (Category)' \
			'  make module shop/order/invoice     models/order/invoice.py (Invoice)' \
			'  make module payment/               modules/payment/ without a model'; \
		exit 1; \
	fi
	$(MANAGE) make_module $(or $(MODULE_NAME),$(NAME))
