from abc import ABC, abstractmethod

from oxytcmri.domain.ports.repositories import Repository


class Importer(ABC):
    """
    Abstract base class for importers to repositories.

    This class serves as a base for all importers, providing a common interface
    and shared functionality.
    """

    @abstractmethod
    def import_data(self):
        """
        Import data from the source.

        This method should be implemented by subclasses to perform the actual
        data import.
        """

    @abstractmethod
    def register_repository(self, repositories: list[Repository]):
        """
        Register needed repositories for the importer, from  a list of repositories.

        Parameters
        ----------
        repositories: list[Repository]
            The list of repositories from which the importer can choose the needed ones.
        """


