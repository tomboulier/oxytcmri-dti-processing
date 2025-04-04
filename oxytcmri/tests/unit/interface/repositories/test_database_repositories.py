# oxytcmri/tests/unit/interface/repositories/test_database_center_repository.py
from typing import Type, Any, Optional

import pytest
from unittest.mock import Mock

from oxytcmri.domain.entities.center import Center
from oxytcmri.domain.entities.mri import DTIMetric, Atlas
from oxytcmri.domain.use_cases.compute_dti_normative_values import NormativeValue, StatisticsStrategies
from oxytcmri.interface.repositories.database_repositories import (
    DataBaseCenterRepository, DataBaseGateway, DataBaseDTINormativeValuesRepository, T)


@pytest.fixture(scope="module")
def mock_gateway():
    """Creates a mock gateway for testing."""
    mock = Mock(spec=DataBaseGateway)
    return mock


class TestDataBaseCenterRepository:
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


class TestDataBaseDTINormativeValuesRepository:
    @pytest.fixture
    def repository(self):
        """Creates a repository instance with the mock gateway."""
        class MockInMemoryDataGateway(DataBaseGateway):
            def __init__(self):
                self.saved_entities = []

            def find_by_id(self, entity_type: Type[T], id_value: Any) -> Optional[T]:
                pass

            def find_by_filters(self, entity_type: Type[T], filters: dict[str, Any]) -> Optional[T]:
                for entity in self.find_all(entity_type):
                    for key, value in filters.items():
                        if not getattr(entity, key) == value:
                            continue
                    return entity
                return None

            def find_all(self, entity_type: Type[T]) -> list[T]:
                return self.saved_entities

            def save(self, entity: T) -> None:
                self.saved_entities.append(entity)

            def delete(self, entity: T) -> None:
                pass

            def update(self, entity: T) -> None:
                pass

        return DataBaseDTINormativeValuesRepository(MockInMemoryDataGateway())

    def test_get_all_normative_values(self, repository, mock_gateway):
        # Arrange
        test_center = Center(id=1, name="Test Center")
        test_atlas_label = 1
        test_atlas = Atlas(id=1, labels=[test_atlas_label])
        test_normative_value = NormativeValue(
            center=test_center,
            dti_metric=DTIMetric.MD,
            atlas=test_atlas,
            atlas_label=1,
            statistic_strategy=StatisticsStrategies.MEAN,
            value=100.0
        )
        repository.save(test_normative_value)

        assert repository.exists(center=test_center,
                                 atlas_label=test_atlas_label,
                                 atlas=test_atlas,
                                 dti_metric=DTIMetric.MD,
                                 statistic_strategy=StatisticsStrategies.MEAN)
