# OxyTCMRI

[![Pytest](https://github.com/tomboulier/oxytcmri-legacy/actions/workflows/pytest.yml/badge.svg)](https://github.com/tomboulier/oxytcmri-legacy/actions/workflows/pytest.yml)
[![codecov](https://codecov.io/gh/tomboulier/oxytcmri-legacy/graph/badge.svg?token=UVPDQPWEYR)](https://codecov.io/gh/tomboulier/oxytcmri-legacy)

Analysis of Diffusion Tensor Imaging (DTI) data from the Oxy-TC trial.

## Overview

**OxyTCMRI** is a Python project designed for the analysis of DTI data from the
<a href="https://www.thelancet.com/journals/laneur/article/PIIS1474-4422(23)00290-9/fulltext">Oxy-TC trial</a>,
a multi-center randomized clinical trial on the use of PbtO<sub>2</sub> probe in neuro-ICU for TBI patients.

This project is part of an ancillary study of the trial. Initially, the Oxy-TC's primary endpoint was to link the volume
of MD lesions, but it was later changed to neurological outcome (assessed with Glasgow Outcome Scale Extended score at 6
months). The ancillary study focuses on the initial primary endpoint: assessing whether PbtO<sub>2</sub> reduces the
volume of DTI lesions. As a secondary endpoint, it examines the relationship between lesion volume and neurological
outcomes.

Currently, this repository focuses on measuring DTI lesion volumes. It provides tools for:

- computing the normative values of DTI metrics (MD, FA, AD, RD) in healthy controls, for each center;
- (work in progress) creating lesions masks for each patient;
- (work in progress) computing the volume of DTI lesions for each patient.

## Installation

Clone the repository:

```bash
    git clone https://github.com/yourusername/OxyTCMRI.git
    cd OxyTCMRI
```

Install dependencies:

``` bash
make install
```

Run the tests to ensure the setup is correct:
```bash
make test
```

### Creating a Settings File

You can use the existing `settings.toml` file as a template for your project.

To create a new settings file for the OxyTCMRI project, you can use the following template.
This file should be in TOML format and include the necessary sections for database configuration, paths, logs,
and brain localizers.

Create a file named `settings.toml` with the following content:

```toml
[database]
path = "path/to/your/database.db"
overwrite_data = true

[paths]
centers_list = "path/to/centers_list.csv"
atlases_list = "path/to/MRI/ROIs/atlases_list.csv"
nifti_files_folder = "path/to/MRI/NiftiFilesFolder"
normative_dti_values_list = "path/to/DTI_normative_values.csv"

[logs]
LogsDirectoryPath = "path/to/logs"
```

Replace the placeholder paths with the actual paths on your system. The CLI commands will use this settings file
to locate and manage the necessary data and configurations.

### (Optional) Creating Symbolic Links to Image Directories

Since the MRI data can be large, it is recommended to create symbolic links to the image directories instead of copying
them. To do this, you can use the `ln -s` command on Unix systems (Linux and Mac). Here is how to proceed:

1. **Open a terminal.**

2. **Use the `ln -s` command to create a symbolic link.** The general syntax is:
   ```bash
   ln -s path/to/source/Nifti/Files/Folder path/to/destination/defined/in/settings
    ```

## Features

The OxyTCMRI Command Line Interface (CLI) offers several features to process and analyze MRI data efficiently. Some of
the key features include:

- Computing normative values of DTI metrics (MD, FA, AD, RD) in healthy controls, for each center.

For more information and help with the project, use the following command:

```bash
python oxytcmricli.py --help
```

### Compute Normative Values

Since DTI data is heavily influenced by the acquisition parameters, it is essential to compute normative values for each
center. The `compute-normative-values` command computes the *normative* values of DTI metrics (MD, FA, AD, RD) in
healthy controls for each center. The term "normative" refers to a set of statistics (mean, standard deviation, median,
interquartile range) that represent the values of DTI metrics in a healthy population, within a single region of
interest inside a given atlas.

```bash
python oxytcmricli.py import-data --settings <settings_filepath> 
                                 [--overwrite_database_file] 
                                 [--dti-metrics <dti_metrics>]
                                 [--statistics-strategies <statistics_strategies>]
```

- `--settings` or `-s`: Path to the settings file (required).
- `--overwrite_database_file` or `-odbf`: Delete the database file if it already exists (default: True).
- `--dti-metrics` or `-dti`: Comma-separated list of DTI metrics to include (e.g. 'FA,MD'). If not provided, all metrics
  will be computed.
- `--statistics-strategies` or `-stats`: Comma-separated list of statistical strategies (e.g. 'mean,std_dev'). If not
  provided, all available strategies will be used.

Data is stored in a SQLite database (which file is specified in the settings file). The format of the table is as
follows:

| id | value       | center_id | dti_metric | atlas_id | atlas_label | statistic_strategy  |
|----|-------------|-----------|------------|----------|-------------|---------------------|
| 1  | 0.001015411 | 1         | FA         | 1        | 1           | mean                |
| 2  | 0.001015411 | 1         | MD         | 2        | 318         | interquartile range |            |

In this table, the column names are:

- `id`: Unique identifier for each entry.
- `value`: The computed value of the DTI metric.
- `center_id`: Identifier for the center where the data was collected.
- `dti_metric`: The DTI metric (e.g., FA, MD) for which the value is computed.
- `atlas_id`: Identifier for the atlas used in the analysis.
- `atlas_label`: Label of the region of interest within the atlas.
- `statistic_strategy`: The statistics used to compute the value (e.g., mean, standard deviation, etc.).


## Documentation

This project uses [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) to build its documentation.

### Build the documentation locally

From the root of the repository:

```bash
make docs
```

This will build the documentation in the `site` directory. You can then open the `index.html` file in your web browser
to view the documentation.

### Serve the documentation locally

To serve the documentation locally, you can use the following command:

```bash
mkdocs serve
```

This will build the documentation, start a local server, which address will be given in the terminal. This server will
automatically reload the documentation when you make changes to the source files.

### Deploy the documentation on GitHub Pages

To deploy the documentation on GitHub Pages, you can use the following command:

```bash
mkdocs gh-deploy
```

This will build the documentation and deploy it to the `gh-pages` branch of your repository. The documentation will be
available at `https://tomboulier.github.io/oxytcmri-legacy/`.
