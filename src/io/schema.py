from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS: set[str] = {"Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"}


class AccVizError(Exception):
    """Base class for all acc_visualisation domain errors."""


@dataclass
class InvalidPlateFolderError(AccVizError):
    path: Path
    reason: str  # "not_exists" | "not_a_dir" | "empty"

    def __str__(self) -> str:
        return f"Invalid plate folder ({self.reason}): {self.path}"


@dataclass
class CsvReadError(AccVizError):
    path: Path
    reason: str  # "encoding" | "separator" | "parse"

    def __str__(self) -> str:
        return f"Could not read CSV ({self.reason}): {self.path}"


@dataclass
class CsvSchemaError(AccVizError):
    path: Path
    missing: set[str] = field(default_factory=set)

    def __str__(self) -> str:
        miss = ", ".join(sorted(self.missing))
        return f"CSV schema error in {self.path}: missing columns {{{miss}}}"


@dataclass
class CsvContentError(AccVizError):
    path: Path
    reason: str  # "too_few_rows" | "all_nan"

    def __str__(self) -> str:
        return f"CSV content error ({self.reason}): {self.path}"
