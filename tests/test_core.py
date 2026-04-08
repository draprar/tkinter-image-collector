"""Core logic tests for FileCollectorCore."""

import os
import stat
from collections.abc import Generator
from pathlib import Path

import pytest

from core import DEFAULT_DATE_FOLDER, FileCollectorCore


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary file with some content."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("abc")
    return file_path


@pytest.fixture
def unreadable_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a file with no read permissions."""
    file_path = tmp_path / "no_read.txt"
    file_path.write_text("secret")
    file_path.chmod(0)
    yield file_path
    try:
        # Restore permissions after test
        file_path.chmod(stat.S_IWUSR | stat.S_IRUSR)
    except FileNotFoundError:
        pass


def test_file_hash_ok(temp_file: Path) -> None:
    """Test SHA-256 hash computation."""
    h = FileCollectorCore.file_hash(temp_file)
    assert isinstance(h, str) and len(h) == 64  # SHA-256 hex digest


def test_file_hash_error(monkeypatch, temp_file: Path) -> None:
    """Test graceful handling of file read errors."""
    def fake_open(*args):
        raise OSError("cannot read file")
    monkeypatch.setattr("builtins.open", fake_open)
    assert FileCollectorCore.file_hash(temp_file) is None


def test_get_date_folder_ok(temp_file: Path) -> None:
    """Test date folder extraction from file mtime."""
    result = FileCollectorCore.get_date_folder(temp_file)
    assert result.count("-") == 2  # Format YYYY-MM-DD


def test_get_date_folder_error(monkeypatch, temp_file: Path) -> None:
    """Test fallback for stat errors."""
    monkeypatch.setattr(Path, "stat", lambda self: (_ for _ in ()).throw(OSError("fail")))
    result = FileCollectorCore.get_date_folder(temp_file)
    assert result == DEFAULT_DATE_FOLDER


def test_get_unique_name_no_conflict(tmp_path: Path) -> None:
    """Test unique name generation without collision."""
    f = FileCollectorCore.get_unique_name(tmp_path, "file.txt")
    assert f == tmp_path / "file.txt"


def test_get_unique_name_with_conflict(tmp_path: Path) -> None:
    """Test unique name generation with collision."""
    existing = tmp_path / "file.txt"
    existing.write_text("x")
    f = FileCollectorCore.get_unique_name(tmp_path, "file.txt")
    assert f.name.startswith("file_1")


def test_categorize_file_known(temp_file: Path) -> None:
    """Test file categorization for known extensions."""
    p = temp_file.with_suffix(".jpg")
    p.write_text("x")
    assert FileCollectorCore.categorize_file(p) == "Images"


def test_categorize_file_other(temp_file: Path) -> None:
    """Test categorization fallback for unknown extensions."""
    p = temp_file.with_suffix(".zzz")
    p.write_text("x")
    assert FileCollectorCore.categorize_file(p) == "OTHER"


def test_filter_files_all(tmp_path: Path) -> None:
    """Test filtering with 'All' category."""
    f1 = tmp_path / "a.jpg"
    f1.write_text("x")
    f2 = tmp_path / "b.txt"
    f2.write_text("x")
    result = FileCollectorCore.filter_files(str(tmp_path), ["All"])
    assert len(result) == 2


def test_filter_files_selected(tmp_path: Path) -> None:
    """Test filtering with specific category."""
    f1 = tmp_path / "a.jpg"
    f1.write_text("x")
    f2 = tmp_path / "b.txt"
    f2.write_text("x")
    result = FileCollectorCore.filter_files(str(tmp_path), ["Images"])
    assert result == [(f1, "Images")]


def test_preview_files_symlink(tmp_path: Path) -> None:
    """Test preview file creation with symlinks."""
    src = tmp_path / "a.txt"
    src.write_text("x")
    temp_dir = tmp_path / "preview"
    FileCollectorCore.preview_files([(src, "OTHER")], temp_dir)
    assert any(temp_dir.iterdir())


def test_preview_files_fallback_copy(monkeypatch, tmp_path: Path) -> None:
    """Test fallback to copy when symlink/hardlink fails."""
    src = tmp_path / "a.txt"
    src.write_text("x")
    temp_dir = tmp_path / "preview"

    def fail_symlink(*args, **kwargs):
        raise OSError("no symlink")
    def fail_link(*args, **kwargs):
        raise OSError("no link")

    monkeypatch.setattr(os, "symlink", fail_symlink)
    monkeypatch.setattr(os, "link", fail_link)

    FileCollectorCore.preview_files([(src, "OTHER")], temp_dir)
    copied_file = temp_dir / "a.txt"
    assert copied_file.exists()


def test_preview_files_name_collision(tmp_path: Path) -> None:
    """Regression: two files with same name should not collide in preview."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    src1 = dir1 / "same.txt"
    src2 = dir2 / "same.txt"
    src1.write_text("content1")
    src2.write_text("content2")
    temp_dir = tmp_path / "preview"
    FileCollectorCore.preview_files([(src1, "OTHER"), (src2, "OTHER")], temp_dir)
    assert (temp_dir / "same.txt").exists()
    assert (temp_dir / "same_1.txt").exists()


def test_collect_selected_files_basic(tmp_path: Path) -> None:
    """Test basic file collection without dry-run."""
    src = tmp_path / "a.txt"
    src.write_text("x")
    files = [(src, "OTHER")]

    copied, renamed, target = FileCollectorCore.collect_selected_files(
        files, tmp_path / "dest", dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )
    assert copied == 1
    assert renamed == 0
    log_file = target / "log.txt"
    assert log_file.exists()


def test_collect_selected_files_dry_run(tmp_path: Path) -> None:
    """Test dry-run mode (no file writes, no log)."""
    src = tmp_path / "a.txt"
    src.write_text("x")
    files = [(src, "OTHER")]
    dest = tmp_path / "dest"

    copied, renamed, target = FileCollectorCore.collect_selected_files(
        files, dest, dry_run=True,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )
    assert copied == 1
    assert renamed == 0
    assert not (target / "log.txt").exists()


def test_collect_selected_files_dry_run_missing_target_dir(tmp_path: Path) -> None:
    """Regression: dry-run should work with missing target directory."""
    src = tmp_path / "a.txt"
    src.write_text("x")
    files = [(src, "OTHER")]
    dest = tmp_path / "missing_dest"

    copied, renamed, target = FileCollectorCore.collect_selected_files(
        files, dest, dry_run=True,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    assert copied == 1
    assert renamed == 0
    assert target == dest
    assert not dest.exists()
    assert not (target / "log.txt").exists()


def test_collect_selected_files_duplicate(tmp_path: Path) -> None:
    """Test deduplication logic (same hash content)."""
    src1 = tmp_path / "a.txt"
    src1.write_text("x")
    src2 = tmp_path / "b.txt"
    src2.write_text("x")
    files = [(src1, "OTHER"), (src2, "OTHER")]
    copied, renamed, target = FileCollectorCore.collect_selected_files(
        files, tmp_path / "dest", dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )
    assert copied == 1
    assert renamed == 1
    assert (target / "log.txt").exists()


def test_collect_selected_files_unreadable_hash(tmp_path: Path, monkeypatch) -> None:
    """Test handling of unreadable files (hash=None)."""
    src = tmp_path / "a.txt"
    src.write_text("x")
    monkeypatch.setattr(FileCollectorCore, "file_hash", lambda _: None)
    files = [(src, "OTHER")]
    copied, renamed, target = FileCollectorCore.collect_selected_files(
        files, tmp_path / "dest", dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )
    assert copied == 0
    assert renamed == 0


def test_check_disk_space_enough(tmp_path: Path, monkeypatch) -> None:
    """Disk preflight returns True when free space is sufficient."""
    src = tmp_path / "a.txt"
    src.write_text("x" * 100)
    files = [(src, "OTHER")]

    class _Usage:
        free = 1024 * 1024

    monkeypatch.setattr("shutil.disk_usage", lambda _: _Usage())
    has_space, required, free = FileCollectorCore.check_disk_space(tmp_path / "dest", files)

    assert has_space is True
    assert required > 0
    assert free == _Usage.free


def test_check_disk_space_insufficient(tmp_path: Path, monkeypatch) -> None:
    """Disk preflight returns False when free space is insufficient."""
    src = tmp_path / "a.txt"
    src.write_text("x" * 10_000)
    files = [(src, "OTHER")]

    class _Usage:
        free = 100

    monkeypatch.setattr("shutil.disk_usage", lambda _: _Usage())
    has_space, required, free = FileCollectorCore.check_disk_space(tmp_path / "dest", files)

    assert has_space is False
    assert required > free

