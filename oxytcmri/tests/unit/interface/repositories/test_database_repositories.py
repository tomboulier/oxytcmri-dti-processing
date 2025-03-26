# oxytcmri/tests/unit/interface/repositories/test_database_center_repository.py
import pytest
from unittest.mock import Mock, MagicMock
from typing import List

from oxytcmri.domain.entities.center import Center
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseGateway)


class TestDataBaseCenterRepository:

    @pytest.fixture
    def mock_gateway(self):
        """Creates a mock gateway for testing."""
        mock = Mock(spec=DataBaseGateway)
        return mock

    @pytest.fixture
    def repository(self, mock_gateway):
        """Creates a repository instance with the mock gateway."""
        return DataBaseCenterRepository(mock_gateway)

    def test_get_all_centers(self, repository, mock_gateway):
        """Tests that the repository can retrieve all centers via the gateway."""
        # Arrange
        expected_centers = [
            Center(id=1, name="Center 1"),
            Center(id=2, name="Center 2")
        ]
        mock_gateway.find_all.return_value = expected_centers

        # Act
        centers = repository.get_all_centers()

        # Assert
        assert centers == expected_centers
        mock_gateway.find_all.assert_called_once_with(Center)

    def test_save_centers(self, repository, mock_gateway):
        """Tests that the repository can save a center via the gateway."""
        # Arrange
        centers = [
            Center(id=1, name="Test Center"),
            Center(id=2, name="Test Center 2")
        ]

        # Act
        repository.save_centers(centers)

        # Assert
        mock_gateway.save_list.assert_called_once_with(centers)
