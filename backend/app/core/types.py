"""
Database type compatibility layer.
Uses PostgreSQL-native types when available, falls back to SQLite-compatible types.
"""

import json
import uuid

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.types import CHAR

from app.core.config import get_settings

_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")


if _is_sqlite:
    class GUID(TypeDecorator):
        """UUID stored as CHAR(36) in SQLite."""
        impl = CHAR(36)
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is not None:
                return str(value)
            return value

        def process_result_value(self, value, dialect):
            if value is not None:
                return uuid.UUID(value)
            return value

    class JSONType(TypeDecorator):
        """JSON stored as TEXT in SQLite."""
        impl = Text
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is not None:
                return json.dumps(value)
            return value

        def process_result_value(self, value, dialect):
            if value is not None:
                return json.loads(value)
            return value

    class ArrayType(TypeDecorator):
        """Array stored as JSON TEXT in SQLite."""
        impl = Text
        cache_ok = True

        def process_bind_param(self, value, dialect):
            if value is not None:
                return json.dumps(value)
            return value

        def process_result_value(self, value, dialect):
            if value is not None:
                return json.loads(value)
            return value

    UUID_TYPE = GUID
    JSON_TYPE = JSONType
    ARRAY_TYPE = ArrayType
else:
    from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, ARRAY

    UUID_TYPE = lambda: PG_UUID(as_uuid=True)
    JSON_TYPE = JSONB
    ARRAY_TYPE = lambda item_type: ARRAY(item_type)
