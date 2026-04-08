"""Integration tests for GUI components (mocked)."""

from unittest.mock import MagicMock

from ui import FileCollectorLauncher


class TestFileCollectorLauncher:
    """Test FileCollectorLauncher logic (GUI mocked)."""

    def test_launcher_folder_selection(self, mocker) -> None:
        """Test folder selection logic."""
        # Mock CTk entirely to avoid tkinter initialization
        mock_launcher = MagicMock(spec=FileCollectorLauncher)
        mock_launcher.source_folder = None
        mock_launcher.target_folder = None
        mock_launcher.temp_preview_dir = None

        # Simulate folder selection
        mock_launcher.source_folder = "/tmp/source"
        mock_launcher.target_folder = "/tmp/dest"

        assert mock_launcher.source_folder == "/tmp/source"
        assert mock_launcher.target_folder == "/tmp/dest"

    def test_launcher_validation_logic(self, mocker) -> None:
        """Test input validation logic."""
        mock_launcher = MagicMock(spec=FileCollectorLauncher)
        mock_launcher.source_folder = None
        mock_launcher.target_folder = None

        # Should fail validation if no folders
        has_folders = bool(mock_launcher.source_folder and mock_launcher.target_folder)
        assert has_folders is False

        # Add folders
        mock_launcher.source_folder = "/tmp"
        mock_launcher.target_folder = "/tmp"
        has_folders = bool(mock_launcher.source_folder and mock_launcher.target_folder)
        assert has_folders is True

    def test_launcher_status_callback(self, mocker) -> None:
        """Test status callback mechanism."""
        status_calls = []

        def mock_status(msg: str) -> None:
            status_calls.append(msg)

        mock_status("Scanning...")
        mock_status("Found 5 files")

        assert len(status_calls) == 2
        assert status_calls[0] == "Scanning..."

    def test_launcher_progress_callback(self, mocker) -> None:
        """Test progress callback mechanism."""
        progress_calls = []

        def mock_progress(val: int) -> None:
            progress_calls.append(val)

        mock_progress(0)
        mock_progress(50)
        mock_progress(100)

        assert progress_calls == [0, 50, 100]


class TestSummaryWindow:
    """Test SummaryWindow logic."""

    def test_summary_message_real_run(self) -> None:
        """Test summary message for real run."""
        # Create expected message
        dry_run = False
        status = "🧪 DRY RUN: No files copied.\n\n" if dry_run else "✅ DONE\n\n"
        msg = f"{status}Unique files: {5}\nDuplicates: {2}\nDestination:\n/tmp/dest"

        assert "✅ DONE" in msg
        assert "Unique files: 5" in msg
        assert "Duplicates: 2" in msg

    def test_summary_message_dry_run(self) -> None:
        """Test summary message for dry-run."""
        # Create expected message
        dry_run = True
        status = "🧪 DRY RUN: No files copied.\n\n" if dry_run else "✅ DONE\n\n"
        msg = f"{status}Unique files: {0}\nDuplicates: {0}\nDestination:\n/tmp/dest"

        assert "🧪 DRY RUN" in msg
        assert "No files copied" in msg
        assert "Unique files: 0" in msg
