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


def test_app_histogram_uses_measured_hist_range_not_interpolated(tmp_path, monkeypatch):
    # Regression guard: das Streamlit-Histogramm muss mit dem gemessenen hist_range
    # gespeist werden, nie mit dem interpolierten z_range (das durch die große
    # Referenz in der Plattenmitte über das Messmaximum hinausschießt).
    from streamlit.testing.v1 import AppTest

    import src.ui.histogram as hist_mod
    from src.core.pipeline import analyze, load_plates
    from src.core.settings import Settings
    from tests.core.conftest import make_plate_folder

    folder = make_plate_folder(
        tmp_path / "p1",
        {(0, 0): 1e-3, (0, 2): 2e-3, (2, 0): 3e-3, (2, 2): 4e-3},
        ref_val=1.0,
    )

    # Erwartetes Ergebnis unabhängig von der App berechnen — mit den App-Defaults
    # (f_min=0, f_max=25000, axis=X, normalize off, interpolate+shared an).
    settings = Settings(
        folders=[("Platte 1", str(folder))],
        f_min=0, f_max=25000, axis="X", normalize=False,
        shared_scale=True, colorscale="Viridis", interpolate=True,
    )
    res = analyze(load_plates(list(settings.folders)).plates, settings)
    expected_hist = res.hist_range
    assert expected_hist is not None
    assert res.z_range is not None and res.z_range[1] > expected_hist[1]  # Overshoot existiert

    captured: dict = {}
    real = hist_mod.make_histogram

    def capturing(values, **kwargs):
        captured["x_range"] = kwargs.get("x_range")
        return real(values, **kwargs)

    monkeypatch.setattr(hist_mod, "make_histogram", capturing)

    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["accviz_folder1"] = str(folder)
    at.run()
    assert not at.exception
    assert captured["x_range"] == expected_hist
