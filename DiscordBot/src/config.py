import os
from bestconfig.config_provider import ConfigProvider
from bestconfig import Config
from typing import Protocol, Iterable


class ServerInfoProtocol(Protocol):
    server: tuple[str, int]
    channel: int
    interval: int


class PermissionCategoryProtocol(Protocol):
    name: str
    channel_id: int
    message_id: int
    title: str
    color: str
    show_group_id: bool
    groups: list[str]


class PermissionGroupsProtocol(Protocol):
    update_delay: int
    categories: list[PermissionCategoryProtocol]


class ConfigFileProtocol(Protocol):
    owners: list[int]
    logging: dict
    permission_groups: PermissionGroupsProtocol
    server_info: ServerInfoProtocol


# чтобы показывались методы из ConfigProvider
class ConfigFileInherited(ConfigFileProtocol, ConfigProvider):
    pass


# по умолчанию список словарей возвращается как list[dict]
# чтобы можно было обращаться как к объектам, элементы списка приводятся к ConfigProvider
original_method = ConfigProvider.get
def __patch(self: ConfigProvider, *args, **kwargs):
    val = original_method(self, *args, **kwargs)
    if isinstance(val, list):
        return [ConfigProvider(v) if isinstance(v, dict) else v for v in val]
    return val
ConfigProvider.get = __patch

instance: ConfigFileInherited = Config() # type: ignore



