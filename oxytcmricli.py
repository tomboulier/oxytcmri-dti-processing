import typer
from oxytcmri.controllers import DatabaseController
from oxytcmri.infrastructure.clinical_data_repositories import CSVAdditionalClinicalDataRepository, \
    ExcelClinicalDataRepository
from oxytcmri.mri_analysis import MRIAnalysis
from oxytcmri.settings import Settings
from oxytcmri.usecases.add_clinical_data import AddClinicalData, AdditionalClinicalData

app = typer.Typer(add_completion=False)


@app.command()
def import_data(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
        database_url: str = typer.Option(None, "--database-url", "-d", help="URL of the database"),
):
    """
    Import data from a CSV file into the database.
    """
    settings = Settings(settings_filepath)

    if database_url is not None:
        settings.database.url = database_url  # Override the database URL if provided

    DatabaseController(settings, overwrite=True).import_data(settings)
    typer.echo("Data imported successfully.")

@app.command()
def add_clinical_data(
        settings_filepath: str = typer.Option(...,
                                              "--settings",
                                              "-s",
                                              help="Path to the settings file"),
        additional_clinical_data_filepath: str = typer.Option(...,
                                                              "--additional-clinical-data-filepath",
                                                              "-acdf",
                                                              help="Path to the additional clinical data file"),
        subject_id_column_name_in_additional_clinical_data : str = typer.Option(
            ...,
            "--additional-subject-id-column-name",
            "-asicn",
            help="Column name for the subject id in the additional clinical data"
        ),
        additional_clinical_data_column_name_in_csv_file: str = typer.Option(
            ...,
            "--additional-clinical-data-column-name-csv",
            "-acdcncsv",
            help="Column name for the additional data"
        ),
        csv_delimiter: str = typer.Option(";",
                                          "--csv-delimiter",
                                          "-cd",
                                          help="Delimiter in the CSV file containing additional clinical data"),
        subject_id_column_name_in_clinical_data_repository : str = typer.Option(
            ...,
            "--repository-subject-id-column-name",
            "-rsicn",
            help="Column name for the subject id in the Excel file containing all other clinical data"
        ),
        additional_clinical_data_column_name_in_excel: str = typer.Option(
            ...,
            "--additional-clinical-data-excel",
            "-acdcnexcel",
            help="Column name for the additional data"
        ),
):
    """
    Add clinical data to the database.

    The additional clinical data file should be a CSV or Excel file with the following columns:
    - a column with the subject ID
    - several columns with the clinical data

    The subject ID is of the form "XX-YY-P", where:
    - "XX" is the site number,
    -"YY" is the subject number,
    - and "P" stands for "patient".
    """
    settings = Settings(settings_filepath)

    additional_clinical_data_repo = CSVAdditionalClinicalDataRepository(
        filepath = additional_clinical_data_filepath,
        subject_id_column_name=subject_id_column_name_in_additional_clinical_data,
        clinical_data_column_name=additional_clinical_data_column_name_in_csv_file,
        delimiter=csv_delimiter,
        )

    clinical_data_repo = ExcelClinicalDataRepository(
        filepath=settings.paths.ClinicalData,
        subject_id_column_name=subject_id_column_name_in_clinical_data_repository
    )

    use_case = AddClinicalData(
        clinical_data_repo=clinical_data_repo,
        additional_clinical_data_repo=additional_clinical_data_repo
    )

    use_case.execute()

    typer.echo("Clinical data added successfully.")


@app.command()
def compute_md_lesions(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
) -> None:
    """
    Compute MD lesions for all subjects and store the results in the database.
    """
    settings = Settings(settings_filepath)

    # open the database
    db_controller = DatabaseController(settings, overwrite=False)
    MRIAnalysis(settings, db_controller).compute_all_mean_diffusivity_lesions_volumes()


@app.command()
def export_data_to_csv(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
        csv_filepath: str = typer.Option(None, "--csv-filepath", "-c", help="Path to the CSV file"),
) -> None:
    """
    Export all MD lesions (high and low) to a CSV file.
    """
    settings = Settings(settings_filepath)

    if csv_filepath is not None:
        settings.paths.MDLesionsCSV = csv_filepath  # Override the CSV file path if provided

    # Create a database controller
    database_controller = DatabaseController(settings, overwrite=False)

    # Export MD lesions to a CSV file
    csv_filepath = settings.paths.MDLesionsCSV if csv_filepath is None else csv_filepath
    database_controller.export_data_to_csv(csv_filepath)

    typer.echo("MD lesions exported successfully.")


@app.command()
def view_md_map(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
        subject_id: str = typer.Option(None, "--subject-id", "-sid", help="Subject ID"),
) -> None:
    """
    View the MD map of a given subject.
    """
    settings = Settings(settings_filepath)
    database_controller = DatabaseController(settings)
    subject = database_controller.get_subject(subject_id)
    subject.view_md_map()


@app.command()
def view_mri(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
        subject_id: str = typer.Option(..., "--subject-id", "-sid", help="Subject ID"),
        volume_name: str = typer.Option(..., "--volume-name", "-vn", help="Volume name"),
        segmentation_name: str = typer.Option(None, "--segmentation-name", "-sn", help="Segmentation name"),
        overlay_name: str = typer.Option(None, "--overlay-name", "-on", help="Overlay name"),
) -> None:
    """
    View the MRI of a given subject.
    """
    settings = Settings(settings_filepath)
    database_controller = DatabaseController(settings)
    subject = database_controller.get_subject(subject_id)
    subject.view_mri(volume_name, segmentation_name, overlay_name)


if __name__ == "__main__":
    app()
