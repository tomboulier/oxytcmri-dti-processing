# Makefile for OxyTCMRI project

SETTINGS_FILE=settings.toml

.PHONY: compute-dti-normative-values test docs

compute-dti-normative-values:
	python main.py compute-dti-normative-values --settings $(SETTINGS_FILE)

test:
	pytest

docs:
	mkdocs build