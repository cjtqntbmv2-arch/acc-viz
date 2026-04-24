from __future__ import annotations

from src.io.schema import (
    AccVizError,
    CsvContentError,
    CsvReadError,
    CsvSchemaError,
    InvalidPlateFolderError,
)
from src.ui import strings as S


def format_error(exc: AccVizError, *, plate_label: str) -> str:
    if isinstance(exc, InvalidPlateFolderError):
        if exc.reason == "not_exists":
            return S.ERROR_PATH_NOT_FOUND.format(path=exc.path)
        if exc.reason == "not_a_dir":
            return S.ERROR_NOT_A_DIR.format(path=exc.path)
        if exc.reason == "empty":
            return S.ERROR_EMPTY_FOLDER.format(path=exc.path)
    if isinstance(exc, CsvReadError):
        return S.ERROR_CSV_READ.format(path=exc.path)
    if isinstance(exc, CsvSchemaError):
        missing = ", ".join(sorted(exc.missing))
        return S.ERROR_CSV_SCHEMA.format(path=exc.path, missing=missing)
    if isinstance(exc, CsvContentError):
        return S.ERROR_CSV_CONTENT.format(path=exc.path)
    return S.ERROR_GENERIC_PLATE.format(label=plate_label, detail=str(exc))
