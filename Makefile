# Kya Khaoon — dev commands. Config comes from the single root .env.
.DEFAULT_GOAL := help
.PHONY: help install dev backend frontend migrate seed wipe reset test stop clean

BE := backend
FE := frontend
DB := $(BE)/dev.db

help:  ## list commands
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

install:  ## set up backend venv + frontend deps
	python3 -m venv $(BE)/.venv
	$(BE)/.venv/bin/pip install -r $(BE)/requirements.txt
	cd $(FE) && npm install

dev:  ## run backend + frontend together (Ctrl+C stops both)
	./run.sh

backend:  ## run just the backend on :8000
	cd $(BE) && ./.venv/bin/uvicorn app.main:app --reload --port 8000

frontend:  ## run just the frontend on :5173
	cd $(FE) && npm run dev

migrate:  ## bring the dev database up to the latest schema
	cd $(BE) && ./.venv/bin/alembic upgrade head

seed:  ## OPTIONAL: load the starter dish catalogue (only the no-LLM fallback uses it)
	cd $(BE) && ./.venv/bin/python -m app.seed

wipe:  ## delete the dev database and recreate it empty
	rm -f $(DB)
# Build the schema from migrations, not SQLModel's create_all. create_all left
# alembic_version empty, so the next `alembic upgrade` replayed from revision 1
# and collided with the tables it had just made.
	@cd $(BE) && ./.venv/bin/alembic upgrade head >/dev/null 2>&1 \
	  && echo "→ database wiped — empty catalogue, the LLM fills it on first deck" \
	  || echo "→ wipe failed: run 'make migrate' to see the error"

reset: wipe  ## alias for wipe

test:  ## run the backend suite (deterministic — no live LLM/Swiggy calls)
	@cd $(BE) && for t in test_auth test_device test_google test_swiggy_oauth test_llm test_llm_ranking test_spice \
	    test_smoke test_cart test_mcp test_mcp_integration; do \
	  printf "  %-22s " $$t; \
	  OPENAI_API_KEY= SWIGGY_MCP_URL= SECRET_KEY=test \
	    ./.venv/bin/python -m tests.$$t >/dev/null 2>&1 && echo PASS || echo FAIL; \
	  rm -f *_test.db smoke.db cart_test.db 2>/dev/null || true; \
	done

stop:  ## kill anything on the dev ports (8000, 5173)
	@lsof -ti :8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti :5173 | xargs kill -9 2>/dev/null || true
	@echo "→ stopped"

clean:  ## remove the db + frontend build (keeps installed deps)
	rm -f $(DB)
	rm -rf $(FE)/dist
	@echo "→ cleaned"
