from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.platform_utils import subprocess_utils


def test_run_hidden_sets_creation_flags_on_windows():
    with patch("src.platform_utils.subprocess_utils.sys") as mock_sys, \
         patch("src.platform_utils.subprocess_utils.subprocess") as mock_sp:
        mock_sys.platform = "win32"
        mock_sp.CREATE_NO_WINDOW = 0x08000000
        mock_sp.run = MagicMock(return_value=MagicMock(returncode=0))
        subprocess_utils.run_hidden(["foo"])
        kwargs = mock_sp.run.call_args.kwargs
        assert kwargs.get("creationflags") == 0x08000000


def test_run_hidden_no_flags_on_posix():
    with patch("src.platform_utils.subprocess_utils.sys") as mock_sys, \
         patch("src.platform_utils.subprocess_utils.subprocess") as mock_sp:
        mock_sys.platform = "darwin"
        mock_sp.run = MagicMock(return_value=MagicMock(returncode=0))
        subprocess_utils.run_hidden(["foo"])
        kwargs = mock_sp.run.call_args.kwargs
        assert "creationflags" not in kwargs
