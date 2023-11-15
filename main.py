from dynaconf import Dynaconf
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from oxytcmri.controllers import DatabaseController
from oxytcmri.models import Base

# Create an instance of Dynaconf for managing settings.
settings = Dynaconf(settings_files=["oxytcmri/test_settings.toml"])


if __name__ == "__main__":
    # read settings
    database_url = settings.database.url
    subjects_list_csv_filepath = settings.paths.SubjectsList
    mri_data_path = settings.paths.MRIData

    # Create a database session
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        # Create a DatabaseController instance and import the data
        database_controller = DatabaseController(db_session)
        database_controller.import_data(subjects_list_csv_filepath, mri_data_path)

        # export all MD lesions (high and low) to a CSV file
        database_controller.export_md_lesions_to_csv("MD_lesions.csv")