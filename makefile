# Makefile for OxyTCMRI project

SETTINGS_FILE = settings.toml
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
UV := $(VENV_DIR)/bin/uv

.PHONY: compute-dti-normative-values test docs install docker-build docker-test

# ensure uv is installed system-wide (fallback)
uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "📦 Installing uv with pip..."; \
		python3 -m pip install --user uv; \
	}

# ensure c3d is installed system-wide (fallback)
c3d:
	@command -v c3d >/dev/null 2>&1 || { \
		echo "📦 Installing c3d..."; \
		wget -O c3d.tar.gz https://sourceforge.net/projects/c3d/files/c3d/Nightly/c3d-nightly-Linux-gcc64.tar.gz/download; \
		mkdir -p /tmp/c3d; \
		tar -xzf c3d.tar.gz -C /tmp/c3d; \
		sudo mv -f /tmp/c3d/c3d-1.4.2-Linux-gcc64/bin/c3d /usr/bin/; \
		rm -f c3d.tar.gz; \
	}

install: uv c3d
	@echo "🔄 Installing base dependencies with uv..."
	@uv sync

install-dev: uv c3d
	@echo "🔧 Installing base + dev dependencies with uv..."
	@uv pip install --group dev

docs: uv
	@echo "📘 Installing doc dependencies and building site..."
	@uv pip install --group docs
	@.venv/bin/mkdocs build

test: install-dev
	@echo "🧪 Running tests..."
	@.venv/bin/pytest

test-coverage: install-dev
	@echo "🧪 Running tests with coverage..."
	@.venv/bin/pytest --cov --cov-branch --cov-report=xml

# Task: launch the DTI normative values computation
compute-dti-normative-values: install
	$(PYTHON) main.py compute-dti-normative-values --settings $(SETTINGS_FILE)

# Docker targets
docker-build:
	@echo "🐳 Building Docker image..."
	@docker build -t oxytcmri:local .

docker-test:
	@echo "🧪 Running tests in Docker container..."
	@docker run --rm --entrypoint python oxytcmri:local -m pytest