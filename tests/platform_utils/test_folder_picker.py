from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.platform_utils import folder_picker


def test_macos_uses_osascript():
    mock_proc = MagicMock(returncode=0, stdout="/Users/x/plate/\n", stderr="")
    with patch("src.platform_utils.folder_picker.sys") as mock_sys, \
         patch("src.platform_utils.folder_picker.run_hidden", return_value=mock_proc) as mock_run:
        mock_sys.platform = "darwin"
        path = folder_picker.pick_folder()
        assert path == "/Users/x/plate"
        assert mock_run.call_args.args[0][0] == "osascript"


def test_macos_nonzero_returns_none():
    mock_proc = MagicMock(returncode=1, stdout="", stderr="cancelled")
    with patch("src.platform_utils.folder_picker.sys") as mock_sys, \
         patch("src.platform_utils.folder_picker.run_hidden", return_value=mock_proc):
        mock_sys.platform = "darwin"
        assert folder_picker.pick_folder() is None


def test_windows_uses_tkinter_inprocess(monkeypatch):
    import sys as real_sys
    monkeypatch.setattr(folder_picker.sys, "platform", "win32", raising=False)

    mock_tk = MagicMock()
    mock_fd = MagicMock()
    mock_fd.askdirectory = MagicMock(return_value="C:/tmp/plate")
    monkeypatch.setitem(real_sys.modules, "tkinter", mock_tk)
    monkeypatch.setitem(real_sys.modules, "tkinter.filedialog", mock_fd)

    path = folder_picker.pick_folder()
    assert path == "C:/tmp/plate"


def test_windows_empty_selection_returns_none(monkeypatch):
    import sys as real_sys
    monkeypatch.setattr(folder_picker.sys, "platform", "win32", raising=False)

    mock_tk = MagicMock()
    mock_fd = MagicMock()
    mock_fd.askdirectory = MagicMock(return_value="")
    monkeypatch.setitem(real_sys.modules, "tkinter", mock_tk)
    monkeypatch.setitem(real_sys.modules, "tkinter.filedialog", mock_fd)

    assert folder_picker.pick_folder() is None
