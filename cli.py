import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from oxytcmri.controllers import DatabaseController
from oxytcmri.models import Base

app = typer.Typer()


@app.command()
def import_data(
        subjects_list_csv_filepath: str = typer.Option(..., "--subjects-list", "-s", help="Path to the CSV file "
                                                                                          "containing the subjects "
                                                                                          "list"),
        mri_data_path: str = typer.Option(..., "--mri-data-path", "-m", help="Path to the MRI data folder"),
        database_url: str = typer.Option(..., "--database-url", "-d", help="URL of the database"),
):
    """
    Import data from a CSV file into the database.
    """
    # Create a database session
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        # Create an ImportController instance
        database_controller = DatabaseController(db_session)

        # Import subjects from the CSV file
        database_controller.import_data(subjects_list_csv_filepath, mri_data_path)

    typer.echo("Data imported successfully.")


if __name__ == "__main__":
    app()
