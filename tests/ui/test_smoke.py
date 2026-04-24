from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_renders_without_folder():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    assert any("Ordnerpfad" in info.value for info in at.info)


def test_app_loads_fixture_plate(smoke_plate_folder):
    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["folder1"] = str(smoke_plate_folder)
    at.run()
    assert not at.exception
    assert len(at.metric) >= 1
