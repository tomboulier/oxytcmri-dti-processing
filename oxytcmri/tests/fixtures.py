from pathlib import Path


def path_to_test_data_folder() -> Path:
    """Returns the path to the test data folder."""
    return (Path(__file__).parent / 'test-data').absolute()
