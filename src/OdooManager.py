try:
    from typing import Self
except ImportError:  # pragma: no cover
    from typing import TypeVar

    Self = TypeVar("Self")


class OdooManager:
    def __init__(self, name: str, database_name: str, database_user: str, database_password: str, admin_password: str,
                 addon_paths: list, host: str):
        self.name = name
        self.database_name = database_name
        self.database_user = database_user
        self.database_password = database_password
        self.admin_password = admin_password
        self.addon_paths = addon_paths
        self.host = host

    def backup(self):
        pass

    @classmethod
    def from_compose(cls, service_definition: dict) -> Self:
        name = service_definition["name"]

        return cls(
            name=name,
            database_name=service_definition["database_name"],
        )
