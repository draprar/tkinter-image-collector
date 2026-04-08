"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def mock_messagebox(mocker):
    """Mock tkinter messagebox dialogs."""
    return {
        "showinfo": mocker.patch("ui.messagebox.showinfo"),
        "showerror": mocker.patch("ui.messagebox.showerror"),
        "askyesno": mocker.patch("ui.messagebox.askyesno", return_value=True),
    }


@pytest.fixture
def mock_filedialog(mocker):
    """Mock tkinter file dialogs."""
    return {
        "askdirectory": mocker.patch("ui.filedialog.askdirectory", return_value="/tmp/test"),
    }

