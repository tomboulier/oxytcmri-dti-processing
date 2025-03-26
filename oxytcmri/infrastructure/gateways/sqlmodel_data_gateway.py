from pathlib import Path
from typing import Type, Any, Optional

from oxytcmri.interface.repositories.database_repositories import DataBaseGateway, T


class SQLModelSQLiteDataGateway(DataBaseGateway):
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        # Ensure that the database file exists
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database file not found: '{self.database_path}'.")

    def find_by_id(self, entity_type: Type[T], id_value: Any) -> Optional[T]:
        pass

    def find_all(self, entity_type: Type[T]) -> list[T]:
        pass

    def save(self, entity: T) -> None:
        pass

    def delete(self, entity: T) -> None:
        pass

    def update(self, entity: T) -> None:
        pass
