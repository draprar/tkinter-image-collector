import os
import tempfile
import hashlib
from unittest import mock
from datetime import datetime
import main


# === HASHING ===
def test_file_hash():
    # SHA-256 hash of file content should match expected value
    with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
        tf.write(b"test content")
        tf.flush()
        h = main.file_hash(tf.name)
    expected = hashlib.sha256(b"test content").hexdigest()
    os.unlink(tf.name)
    assert h == expected


# === DATE FOLDER EXTRACTION ===
def test_get_date_folder_returns_date(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    dt = datetime(2020, 1, 1, 12, 0, 0)
    mod_time = dt.timestamp()
    os.utime(f, (mod_time, mod_time))
    assert main.get_date_folder(f) == "2020-01-01"


def test_get_date_folder_handles_exception():
    class BadPath:
        def stat(self):
            raise Exception("error")
    assert main.get_date_folder(BadPath()) == "no_dates"


# === UNIQUE NAME HANDLING ===
def test_get_unique_name_no_collision(tmp_path):
    fname = "something.txt"
    path = main.get_unique_name(tmp_path, fname)
    assert path.name == fname


def test_get_unique_name_with_collisions(tmp_path):
    base = tmp_path
    fname = "file.txt"
    (base / fname).write_text("a")
    unique_1 = main.get_unique_name(base, fname)
    assert unique_1.name == "file_1.txt"
    (base / unique_1.name).write_text("b")
    unique_2 = main.get_unique_name(base, fname)
    assert unique_2.name == "file_2.txt"


# === SCAN FILES ===
def test_scan_files_filters_correctly(tmp_path):
    doc = tmp_path / "file.pdf"
    img = tmp_path / "img.jpg"
    unknown = tmp_path / "weird.ext"
    doc.write_text("doc")
    img.write_text("img")
    unknown.write_text("???")

    selected = ["Documents", "Images"]
    result = main.scan_files(str(tmp_path), selected)
    names = [f.name for f, _ in result]

    assert "file.pdf" in names
    assert "img.jpg" in names
    assert "weird.ext" not in names


def test_scan_files_all_includes_unknown(tmp_path):
    f = tmp_path / "mystery.xyz"
    f.write_text("???")
    result = main.scan_files(str(tmp_path), ["All"])
    assert len(result) == 1
    assert result[0][1] == "OTHER"


# === COLLECT FILES ===
def test_collect_selected_files_dry_run(tmp_path):
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
    # Two files with identical content (same hash) -> one renamed
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("same content")
    f2.write_text("same content")

    files = [(f1, "Documents"), (f2, "Documents")]
    target_dir = tmp_path / "target"

    copied, renamed, target = main.collect_selected_files(
        files, target_dir,
        dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    assert copied == 1
    assert renamed == 1


def test_collect_selected_files_rename_only(tmp_path):
    # Two files with the same name but different content (hash) -> rename conflict
    f1 = tmp_path / "duplicate.txt"
    f1.write_text("AAA")

    f2_path = tmp_path / "copy"
    f2_path.mkdir()
    f2 = f2_path / "duplicate.txt"
    f2.write_text("BBB")

    files = [(f1, "Documents"), (f2, "Documents")]
    target_dir = tmp_path / "target"

    copied, renamed, target = main.collect_selected_files(
        files, target_dir,
        dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    assert copied == 2
    assert renamed == 1


def test_log_file_is_created(tmp_path):
    src_file = tmp_path / "logme.txt"
    src_file.write_text("data")
    target_dir = tmp_path / "target"

    copied, renamed, _ = main.collect_selected_files(
        [(src_file, "Documents")], target_dir,
        dry_run=False,
        update_status=lambda x: None,
        update_progress=lambda x: None,
    )

    log_path = target_dir / "log.txt"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "COPY" in content or "RENAME" in content
