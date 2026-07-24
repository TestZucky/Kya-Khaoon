# Kya Khaoon — dev commands. Everything runs in containers; config comes from
# the single root .env. There is no host-side venv or node_modules to maintain.
.DEFAULT_GOAL := help
.PHONY: help build dev up down logs backend frontend psql migrate revision seed wipe reset test sh stop clean

DC := docker compose
FE := frontend

help:  ## list commands
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

build:  ## build the images (only needed after a requirements/package.json change)
	$(DC) build

dev: up  ## alias for up

up:  ## run db + backend + frontend in the foreground (Ctrl+C stops them)
	$(DC) up

down:  ## stop everything (keeps the database volume)
	$(DC) down

logs:  ## follow logs from all services
	$(DC) logs -f

backend:  ## follow just the backend logs
	$(DC) logs -f backend

frontend:  ## follow just the frontend logs
	$(DC) logs -f frontend

psql:  ## open a psql shell on the dev database
	$(DC) exec db psql -U kya -d kya_khaoon

migrate:  ## bring the database up to the latest schema
	$(DC) run --rm backend alembic upgrade head

revision:  ## autogenerate a migration:  make revision m="add thing"
	$(DC) run --rm backend alembic revision --autogenerate -m "$(m)"

seed:  ## OPTIONAL: load the starter dish catalogue (only the no-LLM fallback uses it)
	$(DC) run --rm backend python -m app.seed

wipe:  ## destroy the database volume and rebuild the schema from migrations
# Down with -v drops the volume, so the next `up` starts from an empty database
# and the entrypoint's `alembic upgrade head` rebuilds it. Nothing here calls
# create_all — that left alembic_version empty, so the next upgrade replayed
# from revision 1 and collided with the tables it had just made.
	$(DC) down -v
	$(DC) run --rm backend alembic upgrade head
	@echo "→ database wiped — empty catalogue, the LLM fills it on first deck"

reset: wipe  ## alias for wipe

test:  ## run the backend suite in a container against a throwaway Postgres
	$(DC) run --rm tests

sh:  ## shell into the backend container
	$(DC) run --rm backend bash

stop: down  ## alias for down

clean:  ## remove containers, volumes and the frontend build
	$(DC) down -v --remove-orphans
	rm -rf $(FE)/dist
	@echo "→ cleaned"
