# Django Production Boilerplate

Start building product features instead of rebuilding Django infrastructure.

This template provides a practical Django foundation for local development and production deployment, with deliberate defaults and no application-specific architecture to remove.

## Why Use This Template?

- **Production-ready foundation.** Run Django behind Gunicorn and Nginx with HTTPS, secure production settings, health checks, and structured logs.
- **Fast local setup.** Install locked dependencies with uv, use PostgreSQL from day one, and run common tasks through a small Makefile.
- **Deployment flexibility.** Ship with Docker Compose or deploy directly to a Linux host with systemd.
- **Storage that can grow.** Keep uploads on local disk or switch to Amazon S3, Cloudflare R2, MinIO, or another S3-compatible service through environment configuration.
- **Cache and email without provider lock-in.** Select local memory or Redis caching and console, disabled, or SMTP email through environment configuration.
- **A scalable project layout.** Organize features as package-based modules without speculative service, repository, or utility layers.
- **Confidence by default.** CI checks Django configuration, tests, migrations, Compose configuration, and the production image on every change.


## Documentation

Browse the [GitHub Wiki](https://github.com/fahmiauliarahman/django-boilerplate/wiki) for guided documentation for new and experienced Django developers.

## What's Included in the Stack

- Python 3.14, Django 6.0, and PostgreSQL 18
- uv dependency management with a committed lockfile
- Django Unfold admin interface
- Gunicorn, Nginx, WhiteNoise, and HTTPS-ready Compose deployment
- Local and S3-compatible media storage
- Dummy, local-memory, and Redis cache backends
- Console, dummy, and SMTP email backends with a local Mailpit inbox
- Database-aware health check endpoint
- Structured container logging
- Starter tests and GitHub Actions CI
- Environment-based configuration with production security defaults
- Module generator for package-based Django apps

## Quick Start

Install Python through [mise](https://mise.jdx.dev/) or your preferred version manager, then run:

```sh
cp .env.example .env
mise install
uv sync --group cache
docker compose -f compose.yaml -f compose.local.yaml up -d db redis mailpit adminer
uv run python manage.py migrate
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/>.
This runs Django on the host with live reload while PostgreSQL, Redis, Mailpit, and Adminer run in containers.

Create an administrator when needed:

```sh
uv run python manage.py createsuperuser
```

Run the project checks:

```sh
make test
make check
```

Use `make help` to list all available development commands.

## Build Your Application

Feature code lives under `modules/`.
Generate a module, then add more models to it:

```sh
make module shop                    # modules/shop with a Shop model
make module shop.product            # adds models/product.py (Product)
make module shop.catalog.           # adds an empty catalog/ folder (ends with . or /)
make module shop.catalog.category   # adds models/catalog/category.py (Category)
make module shop/order/invoice      # adds models/order/invoice.py (Invoice)
make module payment/                # modules/payment without a model
```

Each run creates the model, Unfold admin, and a starter test, exports them from the package `__init__.py` files, and registers the module in `INSTALLED_APPS`.
Add fields, then run `make makemigrations` and `make migrate`.

The template intentionally leaves product decisions such as APIs, background jobs, cache usage, and social authentication to your application.

See [Extend the boilerplate](docs/extending.md) for a complete feature walkthrough.

## Stack

- Python 3.14
- Django 6.0
- PostgreSQL 18
- Redis 8
- uv
- Docker Compose
- Gunicorn and Nginx

## License

Licensed under the [MIT License](LICENSE).
