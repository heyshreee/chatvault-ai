SHELL := /bin/bash

UV ?= uv
PYTHON ?= .venv/bin/python
NPM ?= npm
VERSION ?= $(shell $(PYTHON) -c "from app.core.config import settings; print(settings.APP_VERSION)" 2>/dev/null || echo 0.0.0)

.PHONY: help setup install frontend-install run dev test test-ollama lint build check tag release clean clean-generated

help:
	@echo "ChatVault AI development targets"
	@echo ""
	@echo "  make setup            Create .venv and install backend dependencies"
	@echo "  make install          Install backend and frontend dependencies"
	@echo "  make run              Start the backend with run.py"
	@echo "  make dev              Start the backend with auto-reload"
	@echo "  make test             Run the backend test suite"
	@echo "  make test-ollama      Run the opt-in real Ollama integration test"
	@echo "  make lint             Compile-check Python and lint the frontend"
	@echo "  make build            Build the production frontend"
	@echo "  make check            Run lint, tests, and the production build"
	@echo "  make tag              Create an annotated tag for the current version"
	@echo "  make clean            Remove caches and frontend build output"
	@echo "  make clean-generated  Remove generated PDF/DOCX exports"

setup:
	$(UV) venv --python 3.13 .venv
	$(UV) pip install --python $(PYTHON) -r requirements.txt
	@test -f .env || cp .env.example .env

frontend-install:
	cd frontend && $(NPM) ci
	@test -f frontend/.env || cp frontend/.env.example frontend/.env

install: setup frontend-install

run:
	$(PYTHON) run.py

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	$(PYTHON) -m pytest -q

test-ollama:
	RUN_OLLAMA_TESTS=1 $(PYTHON) -m pytest -q tests/test_ollama_integration.py

lint:
	$(PYTHON) -m compileall -q app run.py tests
	cd frontend && $(NPM) run lint

build:
	cd frontend && $(NPM) run build

check: lint test build

tag:
	@test "$(VERSION)" != "0.0.0" || (echo "Unable to read APP_VERSION" && exit 1)
	git tag -a "v$(VERSION)" -m "ChatVault AI v$(VERSION)"

release: check tag
	@echo "Created v$(VERSION). Push it with:"
	@echo "  git push origin main --follow-tags"

clean:
	find app tests -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache frontend/dist
	@echo "Removed Python caches and frontend/dist."

clean-generated:
	rm -rf storage/generated/*
	@echo "Removed generated PDF/DOCX exports."
