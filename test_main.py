import pytest
from PIL import Image

from main import collect_images, file_hash, get_unique_name


def create_dummy_image(path):
    img = Image.new('RGB', (10, 10), color='red')
    img.save(path)


def test_file_hash(tmp_path):
    file = tmp_path / "test.jpg"
    create_dummy_image(file)
    expected_hash = file_hash(file)
    assert isinstance(expected_hash, str) and len(expected_hash) == 64


def test_get_unique_name(tmp_path):
    f1 = tmp_path / "file.jpg"
    f1.touch()
    f2 = get_unique_name(tmp_path, "file.jpg")
    assert f2.name.startswith("file_1")


def test_collect_images_basic(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    img1 = src / "img1.jpg"
    img2 = src / "img2.png"
    create_dummy_image(img1)
    create_dummy_image(img2)

    copied, renamed, outdir = collect_images(
        src, dst,
        update_status=lambda _: None,
        update_progress=lambda _: None,
        dry_run=False
    )

    assert copied == 2
    assert renamed == 0
    assert outdir.exists()
    subfolders = list(outdir.glob("*/"))
    assert len(subfolders) == 1  # All images should go into same date folder
    files = list(subfolders[0].glob("*"))
    assert len(files) == 2


def test_collect_images_with_duplicate(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    img1 = src / "dup1.jpg"
    img2 = src / "dup2.jpg"
    content = b"samecontent"
    create_dummy_image(img1)
    create_dummy_image(img2)  # duplicate by content

    copied, renamed, outdir = collect_images(
        src, dst,
        update_status=lambda _: None,
        update_progress=lambda _: None,
        dry_run=False
    )

    assert copied == 1
    assert renamed == 1
    out_files = list(outdir.glob("**/*.jpg"))
    assert len(out_files) == 2
    assert any("_dup" in f.name for f in out_files)


def test_collect_images_dry_run(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    img = src / "dry.jpg"
    create_dummy_image(img)

    copied, renamed, outdir = collect_images(
        src, dst,
        update_status=lambda _: None,
        update_progress=lambda _: None,
        dry_run=True
    )

    # Nothing should be copied in dry run
    assert copied == 1
    assert renamed == 0
    assert not any(dst.glob("**/*.jpg"))
    assert not (outdir / "log.txt").exists()
