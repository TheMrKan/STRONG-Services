# STRONG Python SDK

**Содержит компоненты, используемые в нескольких сервисах, чтобы избежать дублирования кода.**

## Использование
#### 1. Добавить доп. контекст сборки контейнера
```yaml
app:
  build:
    context: .
    additional_contexts:
      sdk: ../PySDK
```

#### 2. Копировать SDK при сборке в Dockerfile
Перед установкой зависимостей через pip
```
COPY --from=sdk . /PySDK/
```

#### 3. Добавить зависимость в requirements.txt (или аналог)
-e для обновления без пересборки
```
-e /PySDK
```

#### 4. Добавить volume для обновления без пересборки
```yaml
volumes:
  - ../PySDK:/PySDK
```

#### 5. Импортировать
```py
import STRONG_SDK
```

## Services
**Python API для взаимодействия с микросервисами.**
В большинстве случаев - простая обертка над HTTPX.

### `player_data.py`
---
Python API для [PlayerDataService](../PlayerDataService/README.md).<br>

**Методы:**

#### `query_async(players: list[int], fields: list[str])`

Endpoint: [/query/](../PlayerDataService/README.md#get-query)<br>
Исключения:
- `PlayerDataServiceError` - ошибка взаимодействия с сервисом.
- `ValueError` - передан пустой `players` или `fields`.

