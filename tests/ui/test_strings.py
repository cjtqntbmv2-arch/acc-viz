from __future__ import annotations
from src.ui import strings as S


def test_required_strings_exist():
    required = [
        "PAGE_TITLE",
        "SIDEBAR_HEADER",
        "FOLDER_PLATE_1",
        "FOLDER_PLATE_2",
        "FREQUENCY_BAND",
        "AXIS",
        "NORMALIZE",
        "SHARED_SCALE",
        "COLORSCALE",
        "PICK_FOLDER",
        "CSV_EXPORT",
        "ERROR_PATH_NOT_FOUND",
        "ERROR_EMPTY_FOLDER",
        "ERROR_CSV_READ",
        "ERROR_CSV_SCHEMA",
        "ERROR_CSV_CONTENT",
        "WAITING_FOR_FOLDER",
    ]
    for name in required:
        val = getattr(S, name)
        assert isinstance(val, str) and val.strip()


def test_error_path_format_has_placeholder():
    assert "{path}" in S.ERROR_PATH_NOT_FOUND
