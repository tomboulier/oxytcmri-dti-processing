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

"""
from pathlib import Path
from typing import Optional

from oxytcmri.models import Subject


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
                ├── subject_id_YY/
                ├── ...
        ├── Patient
            ├── ...

    where XX is the center id and subject_id_YY is the subject id (in lowercase).

    Parameters
    ----------
    data_path: str
        The path to the data folder, containing the folder structure described above.

    subject : Subject
        The subject for which we want to get the path to the folder.

    Returns
    -------
    Path
        The absolute path to the subject folder: `data_path/{Healthy|Patient}/CXX/subject_id_YY`
    """
    subject_type_folder = "Healthy" if subject.subject_type == "Healthy Control" else "Patient"
    subject_folder = f"{data_path}/{subject_type_folder}/C{subject.center.id:02}/{subject.id.lower()}"

    subject_folder_path = Path(subject_folder)

    return subject_folder_path