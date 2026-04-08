"""File collection core logic without UI dependencies."""

import logging
import logging.handlers
import os
import shutil
import time
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# Constants
LOG_MAX_MB = 5
LOG_BACKUPS = 3
HASH_CHUNK_SIZE = 8192
DEFAULT_DATE_FOLDER = "no_dates"
DISK_SAFETY_MARGIN = 1.10

# File types
FILE_TYPES: dict[str, set[str]] = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"},
    "Documents": {".pdf", ".docx", ".txt", ".xlsx", ".csv", ".pptx"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
}


def _load_disk_safety_margin(default: float = DISK_SAFETY_MARGIN) -> float:
    """Load disk safety margin from pyproject.toml; fallback to default on any error."""
    pyproject_path = Path(__file__).with_name("pyproject.toml")
    try:
        if not pyproject_path.exists():
            return default
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        margin = data.get("tool", {}).get("file_collector", {}).get("disk_safety_margin")
        if isinstance(margin, (int, float)) and margin > 0:
            return float(margin)
    except (OSError, tomllib.TOMLDecodeError, AttributeError, TypeError, ValueError):
        logger.warning("Failed to load disk_safety_margin from %s", pyproject_path)
    return default


def setup_logger() -> logging.Logger:
    """Configure application logger with rotation."""
    log_dir = Path.home() / ".file_collector" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "collector.log"

    logger = logging.getLogger("file_collector")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_MB * 1024 * 1024,
            backupCount=LOG_BACKUPS,
            encoding="utf-8",
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        console.setFormatter(formatter)
        logger.addHandler(console)

    logger.debug("Logger initialized")
    return logger


logger = setup_logger()
DISK_SAFETY_MARGIN = _load_disk_safety_margin()


class FileCollectorCore:
    """Core file collection logic without UI."""

    @staticmethod
    def file_hash(filepath: Path) -> Optional[str]:
        """
        Compute SHA-256 hash of a file.

        Args:
            filepath: Path to the file.

        Returns:
            Hex digest of SHA-256 or None on error.
        """
        try:
            import hashlib

            hasher = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(HASH_CHUNK_SIZE):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, ValueError) as exc:
            logger.exception("Hashing failed for %s: %s", filepath, exc)
            return None

    @staticmethod
    def get_date_folder(path: Path) -> str:
        """
        Return folder name (YYYY-MM-DD) based on file modification time.

        Args:
            path: File path.

        Returns:
            Date string or DEFAULT_DATE_FOLDER on failure.
        """
        try:
            return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            logger.warning("Failed to read modification time for %s", path)
            return DEFAULT_DATE_FOLDER

    @staticmethod
    def get_unique_name(base_path: Path, filename: str, suffix: str = "") -> Path:
        """
        Generate a unique path in base_path for filename.

        Args:
            base_path: Directory where file will go.
            filename: Original filename.
            suffix: Optional suffix to add before numbering.

        Returns:
            Path object with a non-colliding filename.
        """
        name, ext = os.path.splitext(filename)
        candidate = base_path / f"{name}{suffix}{ext}"
        i = 1
        while candidate.exists():
            candidate = base_path / f"{name}{suffix}_{i}{ext}"
            i += 1
        return candidate

    @staticmethod
    def categorize_file(path: Path) -> str:
        """
        Categorize a file by its extension.

        Args:
            path: Path of the file.

        Returns:
            Category name or "OTHER".
        """
        ext = path.suffix.lower()
        for category, ext_set in FILE_TYPES.items():
            if ext in ext_set:
                return category
        return "OTHER"

    @staticmethod
    def filter_files(source_dir: str, selected_types: list[str]) -> list[tuple[Path, str]]:
        """
        Walk directory and return list of (file_path, category) filtered by selected_types.

        Args:
            source_dir: Root folder to scan.
            selected_types: Categories to include (may include "All").

        Returns:
            List of tuples (Path, category).
        """
        results: list[tuple[Path, str]] = []
        for root, _, files in os.walk(source_dir):
            for fname in files:
                src_path = Path(root) / fname
                category = FileCollectorCore.categorize_file(src_path)
                if "All" in selected_types or category in selected_types:
                    results.append((src_path, category))
        logger.info("Scanned %s -> found %d files", source_dir, len(results))
        return results

    @staticmethod
    def preview_files(files: list[tuple[Path, str]], temp_dir: Path) -> None:
        """
        Create preview area with symlinks/hardlinks or copies.

        Args:
            files: List of (Path, category).
            temp_dir: Directory to create preview files in.
        """
        os.makedirs(temp_dir, exist_ok=True)
        used_names: set[str] = set()
        for src, _ in files:
            dst = temp_dir / src.name
            # Avoid collision: if filename already used, add numeric suffix.
            if dst.name in used_names:
                base, ext = os.path.splitext(src.name)
                i = 1
                while f"{base}_{i}{ext}" in used_names:
                    i += 1
                dst = temp_dir / f"{base}_{i}{ext}"
            used_names.add(dst.name)
            try:
                # On Windows creating symlinks may require admin; handle gracefully.
                os.symlink(src, dst)
            except (OSError, NotImplementedError) as exc:
                if os.name == "nt":
                    logger.warning(
                        "Symlink failed for %s (Windows may require admin): %s", src, exc
                    )
                else:
                    logger.warning("Symlink failed for %s: %s", src, exc)
                try:
                    os.link(src, dst)
                except (OSError, NotImplementedError):
                    shutil.copy2(src, dst)
                    logger.warning("Fallback to copy for %s", src)

    @staticmethod
    def estimate_total_size(files: list[tuple[Path, str]]) -> int:
        """Estimate total byte size of files, skipping unreadable paths."""
        total_size = 0
        for src_path, _ in files:
            try:
                total_size += src_path.stat().st_size
            except OSError:
                logger.warning("Failed to stat file size for %s", src_path)
        return total_size

    @staticmethod
    def check_disk_space(
        target_dir: Path,
        files: list[tuple[Path, str]],
        safety_margin: float = DISK_SAFETY_MARGIN,
    ) -> tuple[bool, int, int]:
        """
        Check if destination filesystem has enough free space for the copy operation.

        Returns:
            Tuple: (has_space, required_bytes_with_margin, free_bytes).
        """
        required_bytes = int(FileCollectorCore.estimate_total_size(files) * safety_margin)
        usage_base = target_dir if target_dir.exists() else target_dir.parent
        if not usage_base.exists():
            usage_base = Path.cwd()

        free_bytes = shutil.disk_usage(usage_base).free
        has_space = free_bytes >= required_bytes
        return has_space, required_bytes, free_bytes

    @staticmethod
    def collect_selected_files(
        files_to_process: list[tuple[Path, str]],
        target_dir: Path,
        dry_run: bool,
        update_status: Callable[[str], None],
        update_progress: Callable[[int], None],
    ) -> tuple[int, int, Path]:
        """
        Copy files with deduplication and produce a run log.

        Args:
            files_to_process: List of (Path, category) to process.
            target_dir: Destination directory root.
            dry_run: If True, don't actually copy.
            update_status: Callback to update status text (UI thread safe).
            update_progress: Callback to update progress (0-100).

        Returns:
            Tuple of (copied_count, renamed_count, target_dir).
        """
        hashes: dict[str, str] = {}
        copied, renamed = 0, 0
        log_entries: list[str] = []
        total = len(files_to_process) or 1
        start_time = time.time()

        for i, (src_path, category) in enumerate(files_to_process):
            elapsed = time.time() - start_time
            avg_per_file = elapsed / (i + 1)
            remaining = avg_per_file * (total - i - 1)
            eta_str = time.strftime("%Mm %Ss", time.gmtime(remaining))

            # update progress via callback (0-100)
            update_progress(int((i + 1) / total * 100))
            update_status(f"Copying {src_path.name} ({i + 1}/{total}) – ETA: {eta_str}")

            file_h = FileCollectorCore.file_hash(src_path)
            if file_h is None:
                log_entries.append(f"SKIP (unreadable): {src_path}")
                continue

            date_folder = FileCollectorCore.get_date_folder(src_path)
            target_subdir = target_dir / f"{category}_{date_folder}"

            if not dry_run:
                os.makedirs(target_subdir, exist_ok=True)

            if file_h in hashes:
                new_dst = FileCollectorCore.get_unique_name(target_subdir, src_path.name, "_dup")
                log_entries.append(f"DUPLICATE: {src_path} -> {new_dst.relative_to(target_dir)}")
                if not dry_run:
                    shutil.copy2(src_path, new_dst)
                renamed += 1
                continue

            dst_path = FileCollectorCore.get_unique_name(target_subdir, src_path.name)
            if dst_path.name != src_path.name:
                renamed += 1
                log_entries.append(f"RENAME: {src_path.name} -> {dst_path.relative_to(target_dir)}")
            else:
                log_entries.append(f"COPY: {src_path.name} -> {dst_path.relative_to(target_dir)}")

            if not dry_run:
                shutil.copy2(src_path, dst_path)

            hashes[file_h] = dst_path.name
            copied += 1

        if not dry_run:
            os.makedirs(target_dir, exist_ok=True)
            run_log_path = target_dir / "log.txt"
            with open(run_log_path, "w", encoding="utf-8") as f:
                f.write(f"Run log at: {datetime.now()}\n")
                f.write("\n".join(log_entries))
                f.write(f"\n\nFiles copied: {copied}\nDuplicates renamed: {renamed}\n")

        return copied, renamed, target_dir

