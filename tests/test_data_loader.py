from data_loader import load_plate
from tests.conftest import make_csv


def test_load_plate_finds_hole_files(plate_folder):
    hole_data, ref_df = load_plate(str(plate_folder))
    assert (1, 1) in hole_data
    assert (1, 2) in hole_data
    assert (2, 1) in hole_data


def test_load_plate_loads_reference(plate_folder):
    hole_data, ref_df = load_plate(str(plate_folder))
    assert ref_df is not None
    assert "Frequenz_Hz" in ref_df.columns
    assert "PSD_X_g2Hz" in ref_df.columns


def test_load_plate_no_reference(tmp_path):
    make_csv(tmp_path / "x1-y1.csv", 1e-3, 2e-3, 3e-3)
    hole_data, ref_df = load_plate(str(tmp_path))
    assert ref_df is None


def test_load_plate_dataframe_columns(plate_folder):
    hole_data, _ = load_plate(str(plate_folder))
    df = hole_data[(1, 1)]
    assert list(df.columns) == ["Frequenz_Hz", "PSD_X_g2Hz", "PSD_Y_g2Hz", "PSD_Z_g2Hz"]


def test_load_plate_dataframe_row_count(plate_folder):
    hole_data, _ = load_plate(str(plate_folder))
    assert len(hole_data[(1, 1)]) == 5  # 5 frequency points in fixture


def test_load_plate_missing_holes_not_present(plate_folder):
    hole_data, _ = load_plate(str(plate_folder))
    assert (2, 2) not in hole_data  # x2-y2.csv was not created
