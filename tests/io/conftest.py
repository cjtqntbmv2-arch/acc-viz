from __future__ import annotations

from pathlib import Path

CSV_HEADER_LINES = [
    "# Quelle: PicoScope 4000a (Live)",
    "# Spannungsbereich: ±5 V",
    "# Kopplung: AC",
    "# Abtastrate: 50000.00 Hz",
    "# Samples/Block: 131072",
    "# Fensterfunktion: Hanning (ENBW = 1.50)",
    "# Frequenzauflösung: 1.0 Hz",
    "# Mittelung aus 20 Messungen (Leistungsdomäne)",
    "# Empfindlichkeit X/Y/Z: 10.07/10.08/10.78 mV/g",
    "# gRMS-Bereich: 0-25000 Hz",
    "# averaging_method: power",
]


def write_csv(
    path: Path,
    rows: list[tuple[float, float, float, float]],
    *,
    sep: str = ",",
    decimal: str = ".",
    encoding: str = "utf-8",
    header_extra_lines: int = 0,
    bom: bool = False,
) -> None:
    header = "Frequenz_Hz" + sep + sep.join(["PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"])

    def fmt(v: float) -> str:
        s = repr(v)
        return s.replace(".", decimal) if decimal != "." else s

    data_lines = [sep.join(fmt(v) for v in row) for row in rows]

    lines = list(CSV_HEADER_LINES)
    for _ in range(header_extra_lines):
        lines.append("# extra comment")
    lines.append(header)
    lines.extend(data_lines)
    text = "\n".join(lines) + "\n"

    if bom:
        data_bytes = "\ufeff".encode(encoding) + text.encode(encoding)
    else:
        data_bytes = text.encode(encoding)
    path.write_bytes(data_bytes)
