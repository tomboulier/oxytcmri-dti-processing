# OxyTCMRI

[![Pytest](https://github.com/tomboulier/oxytcmri-legacy/actions/workflows/pytest.yml/badge.svg)](https://github.com/tomboulier/oxytcmri-legacy/actions/workflows/pytest.yml)

Analysis of Diffusion Tensor Imaging (DTI) data from the Oxy-TC trial.

## Overview

**OxyTCMRI** is a Python project designed for the analysis of DTI data from the <a href="https://www.thelancet.com/journals/laneur/article/PIIS1474-4422(23)00290-9/fulltext">Oxy-TC trial</a>,
a multi-center randomized clinical trial on the use of PbtO<sub>2</sub> probe in neuro-ICU for TBI patients.

This project is part of an ancillary study of the trial. Initially, the Oxy-TC's primary endpoint was to link the volume of MD lesions, but it was later changed to neurological outcome (assessed with Glasgow Outcome Scale Extended score at 6 months). 

The ancillary study focuses on the initial primary endpoint: assessing whether PbtO<sub>2</sub> reduces the volume of mean diffusivity (MD) lesions. As a secondary endpoint, it examines the relationship between MD lesion volume and neurological outcomes. 

Currently, this repository focuses on measuring MD lesion volumes and linking them with clinical data from the original trial. It provides tools for:
- importing, processing, and exporting patient data;
- computing MD lesion volumes;
- visualizing MD maps, MRI volumes, and overlays.

## Installation

Clone the repository:

```bash
    git clone https://github.com/yourusername/OxyTCMRI.git
    cd OxyTCMRI
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Run the tests to ensure the setup is correct:
```bash
make test
```
### Creating Symbolic Links to Image Directories

To create symbolic links to image directories on Unix systems (Linux and Mac), you 
can use the `ln -s` command. Here is how to do it:

1. **Open a terminal.**

2. **Use the `ln -s` command to create a symbolic link.** The general syntax is:
   ```bash
   ln -s [path/to/source/DTI/directory] data/input/MRI/DTI
   ln -s [path/to/source/structural/directory] data/input/MRI/structural
    ```

### (Optional) Creating a Settings File

You can use the existing `settings.toml` file as a template for your project.

To create a new settings file for the OxyTCMRI project, you can use the following template. 
This file should be in TOML format and include the necessary sections for database configuration, paths, logs, 
and brain localizers.

Create a file named `settings.toml` with the following content:

```toml
[database]
url = "sqlite:///path/to/your/database.db"
overwrite_data = true

[paths]
DTIDataPath = "path/to/dti-data"
StructuralDataPath = "path/to/structural-data"
SubjectsList = "path/to/subjects_list.csv"
MDLesionsCSV = "path/to/results/MD_lesions.csv"
ClinicalData = "path/to/outcomes.xlsx"
PbtO2Data = "path/to/pbtO2.csv"
IGS2Data = "path/to/igs2.xlsx"
ProcessedMRIFolder = "path/to/processed_mri"

[logs]
LogsDirectoryPath = "path/to/logs"
LogsFileName = "oxytcmri.log"

[brainlocalizers]
brain_localizers_list_json_path = "path/to/brain_localizers_list.json"
```

Replace the placeholder paths with the actual paths on your system. This settings file will be used by the CLI commands to locate and manage the necessary data and configurations.

## Features

The OxyTCMRI Command Line Interface (CLI) offers several features to process and analyze MRI data efficiently. Some of the key features include:
- Importing data from a CSV file into the database.
- Computing MD lesions for all subjects and storing the results in the database.
- Exporting all MD lesions (high and low) to a CSV file.
- Viewing the MD map of a given subject.
- Viewing the MRI of a given subject with options for volume, segmentation, and overlay.

For more information and help with the project, use the following command:

```bash
python oxytcmricli.py --help
```

### Import Data

This command imports data from a CSV file into the database.

```bash
python oxytcmricli.py import-data --settings <settings_filepath> [--database-url <database_url>]
```

- `--settings` or `-s`: Path to the settings file.
- `--database-url` or `-d`: (Optional) URL of the database to override the default.

### Compute MD Lesions

This command computes MD lesions for all subjects and stores the results in the database.

```bash
python oxytcmricli.py compute-md-lesions --settings <settings_filepath>
```

- `--settings` or `-s`: Path to the settings file.

### Export Data to CSV

This command exports all MD lesions (high and low) to a CSV file.

```bash
python oxytcmricli.py export-data-to-csv --settings <settings_filepath> [--csv-filepath <csv_filepath>]
```

- `--settings` or `-s`: Path to the settings file.
- `--csv-filepath` or `-c`: (Optional) Path to the CSV file to override the default.

### View MD Map

This command views the MD map of a given subject.

```bash
python oxytcmricli.py view-md-map --settings <settings_filepath> --subject-id <subject_id>
```

- `--settings` or `-s`: Path to the settings file.
- `--subject-id` or `-sid`: Subject ID.

### View MRI

This command views the MRI of a given subject with options for volume, segmentation, and overlay.

```bash
python oxytcmricli.py view-mri --settings <settings_filepath> --subject-id <subject_id> --volume-name <volume_name> [--segmentation-name <segmentation_name>] [--overlay-name <overlay_name>]
```

- `--settings` or `-s`: Path to the settings file.
- `--subject-id` or `-sid`: Subject ID.
- `--volume-name` or `-vn`: Volume name.
- `--segmentation-name` or `-sn`: (Optional) Segmentation name.
- `--overlay-name` or `-on`: (Optional) Overlay name.

### Add clinical data

This command adds clinical data to the database.

```bash
python oxytcmricli.py add-clinical-data ----config <config_filepath>
```

The config file should be in json format and contain the following fields:

```json
{
  "general_settings_filepath": "settings.toml",
  "additional_clinical_data_filepath": "data/input/clinical_data/additional-data.csv",
  "subject_id_column_name_in_additional_clinical_data": "id",
  "additional_clinical_data_column_name_in_csv_file": "column_name",
  "csv_delimiter": ",",
  "subject_id_column_name_in_clinical_data_repository": "id_secondaire",
  "additional_clinical_data_column_name_in_excel": "new_column_name",
  "decoder_function": "lambda x: x"
}
```

This template is given in the `add_clinical_data_config_template.json` file.

## Using the Makefile

The `Makefile` provides a convenient way to run the full data processing pipeline, which includes importing data, computing MD lesions, and exporting the results. 

### Full Pipeline

To run the entire pipeline, simply use the following command in your terminal:

```bash
make
```

This command will execute the full-pipeline target, which includes the following steps:  
- Importing data from the specified CSV file into the database;
- Computing MD lesions for all subjects and storing the results in the database;
- Exporting all MD lesions (high and low) to a CSV file;
- Perform statistical analysis.

### Individual Steps

You can also run each step individually using the following commands:  
- Import Data: `make import-data`
- Compute MD Lesions: `make compute-md-lesions`
- Export Data to CSV: `make export-data-to-csv`

These commands use the `settings.toml` file provided in the repository to locate the necessary data and configurations.

## Documentation

To generate the documentation using Sphinx, use the following commands:

Build the docs:

```bash
cd documentation/
make html
```
