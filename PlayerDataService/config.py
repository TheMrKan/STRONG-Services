from bestconfig import Config
from bestconfig.config_provider import ConfigProvider
from typing import Protocol


class ConfigFileProtocol(Protocol):
    db_host: str
    db_port: int
    db_dbname: str
    db_user: str
    db_password: str



# чтобы показывались методы из ConfigProvider
class ConfigFileInherited(ConfigFileProtocol, ConfigProvider):
    pass


# пробует также получить ключ в верхнем регистре, чтобы по .db_host можно было получить переменную окружения .DB_HOST
def __patch(self: ConfigProvider, item: str, *args, **kwargs):
    try:
        return self.get(item, *args, **kwargs)
    except KeyError:
        return self.get(item.upper(), *args, **kwargs)

ConfigProvider.get = __patch


instance: ConfigFileInherited = Config()  # type: ignore
