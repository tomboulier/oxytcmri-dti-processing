"""
Utility functions for data transformation and analysis.

This module contains various utility functions that are used throughout
the project to perform common tasks such as converting strings to integers
based on specific criteria, and determining sex from initials.

Functions
---------
marshall_score_string_to_int(marshall_score_string)
    Convert a Marshall score represented as a string to an integer.

get_sex_from_initials(initials)
    Determine the sex code ('F' for female, 'M' for male) from initials.

get_subject_folder_path(data_path: str, subject: Subject)
    Get the path to the subject folder.

get_subject_type_from_initials(secondary_id: str) -> str
    Get the subject type from the initials of the secondary id.

gose_evaluation_to_score(gose_evaluation: str) -> Optional[int]
    Convert a GOSE (Glasgow Outcome Scale Extended) evaluation (text) to a GOSE score (numeric).

convert_pbto2_code_to_boolean(code: str) -> Optional[bool]:
    Convert the PbtO2 code ("A" or "B") to the presence of PbtO2 (True or False).

compare_nifti_files(file1_path, file2_path)
    Compare two Nifti files to see if they are equal.
"""
from pathlib import Path
from typing import Optional
import nibabel
import numpy

from oxytcmri.models import Subject, Center


def marshall_score_string_to_int(marshall_score_string: str) -> Optional[int]:
    """Convert a Marshall score (string) to a Marshall score (int).

    Parameters
    ----------
    marshall_score_string : str
        The Marshall score (string).

    Returns
    -------
    int
        The Marshall score (int).

    Raises
    ------
    ValueError
        If the Marshall score is not valid."""
    if marshall_score_string == "I":
        return 1
    elif marshall_score_string == "II":
        return 2
    elif marshall_score_string == "III":
        return 3
    elif marshall_score_string == "IV":
        return 4
    elif marshall_score_string == "Chirurgie d'évacuation d'hématome":
        return 5
    elif marshall_score_string == "Hématome massif non évacué":
        return 6
    else:
        return None


def get_sex_from_initials(initials):
    """
    Convert initials into sex code.
    Returns 'F' or 'M' if the initials are 'F' or 'M' respectively.
    If anything else, or if the type of initials is not str, returns "nan".

    Parameters
    ----------
    initials : str

    Returns
    -------
    str
    """
    if not isinstance(initials, str) and initials not in ["F", "M"]:
        return "nan"
    return initials


def get_subject_folder_path(data_path: str, subject: Subject) -> Path:
    """Get the path to the subject folder.

    MRI Volumes from Pixyl are organized in a tree directory with the
    following structure:

    .. code-block:: text

        ├── Healthy/
           ├── CXX/
                ├── subject_id/
                ├── ...
        ├── Patient/
            ├── ...

    where XX is the center id and subject_id is in lowercase.

    Parameters
    ----------
    data_path: str
        The path to the data folder, containing the folder structure described above.

    subject : Subject
        The subject for which we want to get the path to the folder.

    Returns
    -------
    Path
        The absolute path to the subject folder: `data_path/{Healthy|Patient}/CXX/subject_id`
    """
    subject_type_folder = "Healthy" if subject.subject_type == "Healthy Control" else "Patient"
    subject_folder = f"{data_path}/{subject_type_folder}/C{subject.center.id:02}/{subject.id.lower()}"

    subject_folder_path = Path(subject_folder)

    return subject_folder_path


def create_tree_structure(root_directory: Path, db_controller: 'DatabaseController') -> None:
    """
    Create the tree structure for the data.

    MRI Volumes from Pixyl are organized in a tree directory with the following structure:

    .. code-block:: text

        ├── Healthy/
           ├── CXX/
                ├── subject_id/
                ├── ...
        ├── Patient/
            ├── ...

    where XX is the center id and subject_id is in lowercase.

    Parameters
    ----------
    root_directory: Path
        The path to the data folder, containing the folder structure described above.

    db_controller: DatabaseController
        The database controller.
    """
    # verify if the tree structure already exists
    if not root_directory.exists():
        raise ValueError(f"Cannot create data structure folders in {root_directory} because it does not exist")

    # create the tree structure
    for subject in db_controller.get_all_subjects():
        subject_folder_path = get_subject_folder_path(str(root_directory), subject)
        subject_folder_path.mkdir(parents=True, exist_ok=True)


def get_subject_type_from_initials(secondary_id: str) -> str:
    """Get the subject type from the initials of the secondary id.

    Parameters
    ----------
    secondary_id : str
        The secondary id.

    Returns
    -------
    str
        The subject type, which is either "Healthy Control", "Patient" or "Patient Test".

    Raises
    ------
    ValueError
        If the initials are not "V", "P" or "T".
    """
    initials = secondary_id[6]
    if initials == "V":
        return "Healthy Control"
    elif initials == "P":
        return "Patient"
    elif initials == "T":
        return "Patient Test"
    else:
        raise ValueError(f"Invalid subject type: {initials}")


def gose_evaluation_to_score(gose_evaluation: str) -> Optional[int]:
    """onvert a GOSE (Glasgow Outcome Scale Extended) evaluation (text) to a GOSE score (numeric).

    Parameters
    ----------
    gose_evaluation : str
        The GOSE evaluation.

    Returns
    -------
    int
        The GOSE score.

    Raises
    ------
    ValueError
        If the GOSE evaluation is not valid."""
    if gose_evaluation == "":
        return None
    else:
        return int(gose_evaluation[-2])


def convert_pbto2_code_to_boolean(code: str) -> Optional[bool]:
    """Convert the PbtO2 code ("A" or "B") to the presence of PbtO2 (True or False).
    In the CSV file, the PbtO2 code is written as "A" or "B", where:
    - "A" means that the patient is not monitored with PbtO2,
    - "B" means that the patient is monitored with PbtO2.

    Parameters
    ----------
    code : str
        The PbtO2 code.

    Returns
    -------
    bool
        True if the patient has PbtO2, False otherwise.

    Raises
    ------
    ValueError
        If the PbtO2 code is not valid.
    """
    if code == "A":
        return False
    elif code == "B":
        return True
    else:
        raise ValueError(f"Invalid PbtO2 code: {code}")


def compare_nifti_files(file1_path, file2_path):
    # Load the Nifti files
    img1 = nibabel.load(file1_path)
    img2 = nibabel.load(file2_path)

    # Get the data from the Nifti files
    data1 = img1.get_fdata()
    data2 = img2.get_fdata()

    # Compare the data
    return numpy.array_equal(data1, data2)
