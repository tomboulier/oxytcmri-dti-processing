import json

import typer
from oxytcmri.controllers import DatabaseController
from oxytcmri.infrastructure.clinical_data_repositories import CSVAdditionalClinicalDataRepository, \
    ExcelClinicalDataRepository
from oxytcmri.mri_analysis import MRIAnalysis
from oxytcmri.settings import Settings
from oxytcmri.usecases.add_clinical_data import AddClinicalData, ClinicalDataDecoder
from oxytcmri.usecases.statistical_analysis import OxyTCResultsBuilder, MultivariateLogisticRegressionAnalyzer, \
    BaseLineCharacteristicsTable

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
def add_clinical_data(config_filepath: str = typer.Option(
    ...,
    "--config",
    "-c",
    help="Path to the json configuration file")
):
    """
    Add clinical data to the database using a configuration file.
    """
    with open(config_filepath, 'r') as file:
        config = json.load(file)

    settings = Settings(config["general_settings_filepath"])

    additional_clinical_data_repo = CSVAdditionalClinicalDataRepository(
        filepath=config["additional_clinical_data_filepath"],
        subject_id_column_name=config["subject_id_column_name_in_additional_clinical_data"],
        clinical_data_column_name=config["additional_clinical_data_column_name_in_csv_file"],
        delimiter=config["csv_delimiter"],
    )

    clinical_data_repo = ExcelClinicalDataRepository(
        filepath=settings.paths.ClinicalData,
        subject_id_column_name=config["subject_id_column_name_in_clinical_data_repository"]
    )

    clinical_data_decoder = ClinicalDataDecoder(
        new_name=config["additional_clinical_data_column_name_in_excel"],
        decoder=eval(config["decoder_function"])
    )

    use_case = AddClinicalData(
        clinical_data_repo=clinical_data_repo,
        additional_clinical_data_repo=additional_clinical_data_repo,
        clinical_data_decoder=clinical_data_decoder
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
def statistical_analysis(
        settings_filepath: str = typer.Option(...,
                                              "--settings",
                                              "-s",
                                              help="Path to the settings file",
                                              ),
) -> None:
    """
    Perform a statistical analysis on the data.
    """
    settings = Settings(settings_filepath)

    # Load the data
    analysis_population = settings.statanalysis.analysis_population
    oxytc_results = OxyTCResultsBuilder(
        analysis_population=analysis_population
    ).from_csv(settings.paths.MDLesionsCSV)

    # Baseline characteristics table
    table = BaseLineCharacteristicsTable(oxytc_results)

    print(table)
    table.to_excel(settings.statanalysis.statistics_excel_output_path)

    # Perform a multivariate logistic regression analysis
    additional_variables = settings.statanalysis.additional_variables

    analyzer = MultivariateLogisticRegressionAnalyzer(data_frame=oxytc_results.to_dataframe(),
                                                      mandatory_variables=["age"],
                                                      independent_variables=additional_variables,
                                                      dependant_variable="unfavorable_outcome",
                                                      start_variable="sum_MD_lesions_in_mL_7_94_whole_brain")
    logistic_regression_analysis_results = analyzer.perform_analysis()

    print(logistic_regression_analysis_results)


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
