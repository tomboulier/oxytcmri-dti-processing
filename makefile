# Makefile for OxyTCMRI project

SETTINGS_FILE = settings.toml
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
UV := $(VENV_DIR)/bin/uv

.PHONY: compute-dti-normative-values test docs install

# Task: install dependencies
install: uv
	@echo "🔄 Syncing base dependencies with uv..."
	@$(UV) sync

# Task: create virtual environment if it doesn't exist
$(VENV_DIR)/bin/activate:
	@echo "🔍 Checking virtualenv in $(VENV_DIR)..."
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "⚙️  Creating virtual environment..."; \
		if command -v virtualenv >/dev/null 2>&1; then \
			echo "➕ Using virtualenv"; \
			virtualenv $(VENV_DIR); \
		else \
			echo "➕ Using built-in venv"; \
			python -m venv $(VENV_DIR); \
		fi; \
		$(PIP) install --upgrade pip; \
	fi

# Ensure uv is installed in the venv
uv: $(VENV_DIR)/bin/activate
	@echo "🔍 Checking for uv..."
	@if ! [ -x "$(UV)" ]; then \
		echo "📦 Installing uv in venv..."; \
		$(PIP) install uv; \
	fi


# Task: run tests
test:
	$(PYTHON) -m pytest

# Task: build documentation
docs:
	$(PYTHON) -m mkdocs build

# Task: launch the DTI normative values computation
compute-dti-normative-values:
	$(PYTHON) main.py compute-dti-normative-values --settings $(SETTINGS_FILE)