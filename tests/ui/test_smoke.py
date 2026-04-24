from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_renders_without_folder():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    assert any("Ordnerpfad" in info.value for info in at.info)


def test_app_loads_fixture_plate(smoke_plate_folder):
    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["accviz_folder1"] = str(smoke_plate_folder)
    at.run()
    assert not at.exception
    assert len(at.metric) >= 1


def test_partial_load_shows_error_and_continues(tmp_path, monkeypatch):
    from tests.io.conftest import write_csv

    good = tmp_path / "good"
    good.mkdir()
    good_rows = [(f, 1e-3, 2e-3, 3e-3) for f in (0.0, 1.0, 2.0, 3.0, 4.0)]
    write_csv(good / "x1-y1.csv", good_rows)
    write_csv(good / "Referenz.csv", good_rows)

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "x1-y1.csv").write_text("# junk\nFrequenz_Hz,PSD_X_g2Hz\n0.0,1e-3\n1.0,1e-3\n")

    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["accviz_folder1"] = str(good)
    at.session_state["accviz_folder2"] = str(bad)
    at.run()
    assert not at.exception
    assert len(at.error) >= 1
    assert len(at.metric) >= 1 or any(
        "heatmap" in (getattr(el, "key", "") or "") for el in at.main
    )
