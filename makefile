# Makefile for OxyTCMRI project

SETTINGS_FILE = settings.toml
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
UV := $(VENV_DIR)/bin/uv

.PHONY: compute-dti-normative-values test docs install

# ensure uv is installed system-wide (fallback)
uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "📦 Installing uv with pip..."; \
		python3 -m pip install --user uv; \
	}

install: uv
	@echo "🔄 Installing base dependencies with uv..."
	@uv sync

install-dev: uv
	@echo "🔧 Installing base + dev dependencies with uv..."
	@uv pip install --group dev

docs: uv
	@echo "📘 Installing doc dependencies and building site..."
	@uv pip install --group docs
	@.venv/bin/mkdocs build

test: install-dev
	@echo "🧪 Running tests..."
	@.venv/bin/pytest

# Task: launch the DTI normative values computation
compute-dti-normative-values: install
	$(PYTHON) main.py compute-dti-normative-values --settings $(SETTINGS_FILE)