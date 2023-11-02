import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from oxytcmri.controllers import ImportController
from oxytcmri.models import Base

app = typer.Typer()


@app.command()
def import_data(
        csv_file: str = typer.Option(..., "--csv-file", "-c", help="Path to the CSV file"),
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
        import_controller = ImportController(db_session)

        # Import subjects from the CSV file
        import_controller.import_subjects_from_csv(csv_file)

    typer.echo("Data imported successfully.")


if __name__ == "__main__":
    app()
