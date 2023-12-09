import typer
from dynaconf import Dynaconf
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from oxytcmri.controllers import DatabaseController
from oxytcmri.models import Base

app = typer.Typer(add_completion=False)


@app.command()
def import_data(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
        subjects_list_csv_filepath: str = typer.Option(None, "--subjects-list", "-sl", help="Path to the CSV file "
                                                                                            "containing the subjects "
                                                                                            "list"),
        mri_data_path: str = typer.Option(None, "--mri-data-path", "-m", help="Path to the MRI data folder"),
        database_url: str = typer.Option(None, "--database-url", "-d", help="URL of the database"),
):
    """
    Import data from a CSV file into the database.
    """
    # Create an instance of Dynaconf for managing settings.
    settings = Dynaconf(settings_files=[settings_filepath])

    # Create a database controller
    database_url = settings.database.url if database_url is None else database_url
    database_controller = DatabaseController(database_url)

    # Import subjects from the CSV file
    mri_data_path = settings.paths.MRIData if mri_data_path is None else mri_data_path
    subjects_list_csv_filepath = settings.paths.SubjectsList if subjects_list_csv_filepath is None else subjects_list_csv_filepath
    database_controller.import_data(subjects_list_csv_filepath, mri_data_path)

    typer.echo("Data imported successfully.")


@app.command()
def export_md_lesions_to_csv(
        settings_filepath: str = typer.Option(..., "--settings", "-s", help="Path to the settings file"),
        database_url: str = typer.Option(None, "--database-url", "-d", help="URL of the database"),
        csv_filepath: str = typer.Option(None, "--csv-filepath", "-c", help="Path to the CSV file"),
) -> None:
    """
    Export all MD lesions (high and low) to a CSV file.
    """
    # Create an instance of Dynaconf for managing settings.
    settings = Dynaconf(settings_files=[settings_filepath])

    # Create a database controller
    database_url = settings.database.url if database_url is None else database_url
    database_controller = DatabaseController(database_url)

    # Export MD lesions to a CSV file
    csv_filepath = settings.paths.MDLesionsCSV if csv_filepath is None else csv_filepath
    database_controller.export_md_lesions_to_csv(csv_filepath)

    typer.echo("MD lesions exported successfully.")


if __name__ == "__main__":
    app()
