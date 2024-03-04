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

from typing import Optional


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
