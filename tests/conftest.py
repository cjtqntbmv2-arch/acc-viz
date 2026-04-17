import textwrap
import pytest
from pathlib import Path

CSV_HEADER = textwrap.dedent("""\
    # Quelle: PicoScope 4000a (Live)
    # Spannungsbereich: ±5 V
    # Kopplung: AC
    # Abtastrate: 50000.00 Hz
    # Samples/Block: 131072
    # Fensterfunktion: Hanning (ENBW = 1.50)
    # Frequenzauflösung: 1.0 Hz
    # Mittelung aus 20 Messungen (Leistungsdomäne)
    # Empfindlichkeit X/Y/Z: 10.07/10.08/10.78 mV/g
    # gRMS-Bereich: 0–25000 Hz
    # averaging_method: power
    Frequenz_Hz,PSD_X_g2Hz,PSD_Y_g2Hz,PSD_Z_g2Hz
""")


def make_csv(path: Path, psd_x: float, psd_y: float, psd_z: float, freqs=(0.0, 1.0, 2.0, 3.0, 4.0)):
    lines = CSV_HEADER
    for f in freqs:
        lines += f"{f},{psd_x},{psd_y},{psd_z}\n"
    path.write_text(lines)


@pytest.fixture
def plate_folder(tmp_path):
    make_csv(tmp_path / "x1-y1.csv", psd_x=1e-3, psd_y=2e-3, psd_z=3e-3)
    make_csv(tmp_path / "x1-y2.csv", psd_x=2e-3, psd_y=4e-3, psd_z=6e-3)
    make_csv(tmp_path / "x2-y1.csv", psd_x=4e-3, psd_y=8e-3, psd_z=12e-3)
    make_csv(tmp_path / "Referenz.csv", psd_x=1e-3, psd_y=2e-3, psd_z=3e-3)
    return tmp_path
