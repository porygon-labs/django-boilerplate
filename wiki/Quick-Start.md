# Quick Start

This path runs Django on the host with live reload while PostgreSQL, Redis, Mailpit, and Adminer run in containers.

## Requirements

- Python 3.14
- `mise` or another Python version manager
- `uv`
- Docker Engine with Docker Compose v2
- macOS, Linux, or Windows with WSL 2

## Start the Project

```sh
make setup
make run
```

`make setup` creates `.env` from `.env.example` when missing, installs Python and dependencies, starts local services, and applies migrations.
It is safe to run again.

On Windows, run these commands inside [WSL 2](https://learn.microsoft.com/windows/wsl/install).
The Makefile uses POSIX shell commands, so it does not run from PowerShell or `cmd`.
Without WSL, call the Django commands directly, for example `uv run python manage.py make_module shop.product`.

Open <http://127.0.0.1:8000/>.

Local services:

| Service | Address | Purpose |
| --- | --- | --- |
| Django | <http://127.0.0.1:8000/> | Application development server |
| PostgreSQL | `127.0.0.1:5432` | Application database |
| Redis | `127.0.0.1:6379` | Shared cache |
| Mailpit | <http://localhost:8025> | Captured development email |
| Adminer | <http://localhost:8080> | Database browser |

## Create an Administrator

```sh
make superuser
```

Stop the local services with `make services-down`, and start them again with `make services`.

## Run Checks

```sh
make test
make check
```

## Next Step

Follow [Extending the Boilerplate](Extending-the-Boilerplate) to build and test a complete Django module.
