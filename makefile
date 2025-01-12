# Makefile for OxyTCMRI project

SETTINGS_FILE=settings.toml

.PHONY: full-pipeline import-data compute-md-lesions export-data test

full-pipeline: import-data compute-md-lesions export-data stats

import-data:
	python oxytcmricli.py import-data --settings $(SETTINGS_FILE)

compute-md-lesions:
	python oxytcmricli.py compute-md-lesions --settings $(SETTINGS_FILE)

stats:
	python oxytcmricli.py statistical-analysis --settings $(SETTINGS_FILE)

export-data:
	python oxytcmricli.py export-data-to-csv --settings $(SETTINGS_FILE)

test:
	pytest

# Set the default target to full-pipeline
.DEFAULT_GOAL := full-pipeline
