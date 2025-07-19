import tempfile
import os
from unittest import mock
import hashlib
from datetime import datetime
from pathlib import Path
import main
from main import FILE_TYPES

def test_file_hash():
    # Test that file_hash returns correct SHA-256 hash of file content
    with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
        tf.write(b"test content")
        tf.flush()
        h = main.file_hash(tf.name)
    expected = hashlib.sha256(b"test content").hexdigest()
    os.unlink(tf.name)
    assert h == expected

def test_get_date_folder_returns_date(tmp_path):
    # Test get_date_folder returns formatted modification date string
    f = tmp_path / "file.txt"
    f.write_text("hello")
    dt = datetime(2020, 1, 1, 12, 0, 0)
    mod_time = dt.timestamp()
    os.utime(f, (mod_time, mod_time))
    assert main.get_date_folder(f) == "2020-01-01"

def test_get_date_folder_handles_exception():
    # Test get_date_folder returns "no_dates" if stat() raises Exception
    class BadPath:
        def stat(self):
            raise Exception("error")
    assert main.get_date_folder(BadPath()) == "no_dates"

def test_get_unique_name(tmp_path):
    # Test get_unique_name returns a unique filename if the original exists
    base = tmp_path
    fname = "file.txt"
    (base / fname).write_text("a")
    unique_name = main.get_unique_name(base, fname)
    assert unique_name.name == "file_1.txt"
    (base / "file_1.txt").write_text("b")
    unique_name2 = main.get_unique_name(base, fname)
    assert unique_name2.name == "file_2.txt"

def scan_files(source_dir, selected_types):
    all_files = [Path(root) / f for root, _, files in os.walk(source_dir) for f in files]
    results = []

    for src_path in all_files:
        ext = src_path.suffix.lower()
        matched = None
        for category, ext_set in FILE_TYPES.items():
            if ext in ext_set and (category in selected_types or "All" in selected_types):
                matched = category
                break
        # Skip files with unknown extension, even if "All" selected
        if matched is None:
            continue

        results.append((src_path, matched))
    return results

def test_collect_selected_files_dry_run(tmp_path):
    # Test collect_selected_files with dry_run=True does not copy files
    src_file = tmp_path / "test.txt"
    src_file.write_text("content")
    files_to_process = [(src_file, "Documents")]

    target_dir = tmp_path / "target"
    copied, renamed, target = main.collect_selected_files(
        files_to_process,
        target_dir,
        dry_run=True,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    assert copied == 1
    assert renamed == 0
    assert target == target_dir
    assert not target_dir.exists()

@mock.patch("shutil.copy2")
def test_collect_selected_files_real_copy(mock_copy, tmp_path):
    # Test collect_selected_files with dry_run=False calls shutil.copy2
    src_file = tmp_path / "test.txt"
    src_file.write_text("content")
    files_to_process = [(src_file, "Documents")]

    target_dir = tmp_path / "target"
    copied, renamed, target = main.collect_selected_files(
        files_to_process,
        target_dir,
        dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    assert copied == 1
    assert renamed == 0
    assert target == target_dir
    mock_copy.assert_called_once()

@mock.patch("shutil.copy2")
def test_collect_selected_files_duplicate(mock_copy, tmp_path):
    # Test collect_selected_files detects duplicate files by hash and renames duplicates
    f1 = tmp_path / "file1.txt"
    f1.write_text("same content")
    f2 = tmp_path / "file2.txt"
    f2.write_text("same content")

    files_to_process = [(f1, "Documents"), (f2, "Documents")]

    target_dir = tmp_path / "target"
    copied, renamed, target = main.collect_selected_files(
        files_to_process,
        target_dir,
        dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    assert copied == 1  # one unique file
    assert renamed == 1  # one duplicate renamed
