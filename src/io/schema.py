from __future__ import annotations

"""Shared CSV column schema and domain-specific exception types."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

FREQUENCY_COLUMN = "Frequenz_Hz"
PSD_COLUMNS = ("PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz")
REQUIRED_COLUMNS: set[str] = {FREQUENCY_COLUMN, *PSD_COLUMNS}


class AccVizError(Exception):
    """Base class for all acc_visualisation domain errors."""


@dataclass
class InvalidPlateFolderError(AccVizError):
    path: Path
    reason: Literal["not_exists", "not_a_dir", "empty"]

    def __post_init__(self) -> None:
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        return f"Invalid plate folder ({self.reason}): {self.path}"


@dataclass
class CsvReadError(AccVizError):
    path: Path
    reason: Literal["encoding", "separator", "parse"]

    def __post_init__(self) -> None:
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        return f"Could not read CSV ({self.reason}): {self.path}"


@dataclass
class CsvSchemaError(AccVizError):
    path: Path
    missing: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        miss = ", ".join(sorted(self.missing))
        return f"CSV schema error in {self.path}: missing columns {{{miss}}}"


@dataclass
class CsvContentError(AccVizError):
    path: Path
    reason: Literal["too_few_rows", "all_nan"]

    def __post_init__(self) -> None:
        Exception.__init__(self, str(self))

    def __str__(self) -> str:
        return f"CSV content error ({self.reason}): {self.path}"
