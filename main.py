import logging
import logging.handlers
import os
import shutil
import tempfile
import threading
import hashlib
import time
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional

from tkinter import filedialog, messagebox
import customtkinter as ctk

# =====================================================
# Global configuration
# =====================================================

# UI
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# File types
FILE_TYPES: dict[str, set[str]] = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"},
    "Documents": {".pdf", ".docx", ".txt", ".xlsx", ".csv", ".pptx"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
}

# Conf
LOG_MAX_MB = 5
LOG_BACKUPS = 3
HASH_CHUNK_SIZE = 8192


# =====================================================
# Logger
# =====================================================
def setup_logger() -> logging.Logger:
    log_dir = Path.home() / ".file_collector" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "collector.log"

    logger = logging.getLogger("file_collector")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=LOG_MAX_MB * 1024 * 1024,
            backupCount=LOG_BACKUPS, encoding="utf-8"
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


# =====================================================
# Core logic
# =====================================================
class FileCollectorCore:
    """Pure logic."""

    @staticmethod
    def file_hash(filepath: Path) -> Optional[str]:
        """Returns SHA-256 or None when error."""
        try:
            hasher = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(HASH_CHUNK_SIZE):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.exception("Hashing failed for %s: %s", filepath, e)
            return None

    @staticmethod
    def get_date_folder(path: Path) -> str:
        """Dir based on modification date."""
        try:
            return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        except Exception:
            logger.warning("Failed to read modification time for %s", path)
            return "no_dates"

    @staticmethod
    def get_unique_name(base_path: Path, filename: str, suffix: str = "") -> Path:
        """Returns unique path."""
        name, ext = os.path.splitext(filename)
        candidate = base_path / f"{name}{suffix}{ext}"
        i = 1
        while candidate.exists():
            candidate = base_path / f"{name}{suffix}_{i}{ext}"
            i += 1
        return candidate

    @staticmethod
    def categorize_file(path: Path) -> str:
        ext = path.suffix.lower()
        for category, ext_set in FILE_TYPES.items():
            if ext in ext_set:
                return category
        return "OTHER"

    @staticmethod
    def scan_files(source_dir: str, selected_types: list[str]) -> list[tuple[Path, str]]:
        """Scans dir and returns list: path, category."""
        results = []
        for root, _, files in os.walk(source_dir):
            for fname in files:
                src_path = Path(root) / fname
                cat = FileCollectorCore.categorize_file(src_path)
                if "All" in selected_types or cat in selected_types:
                    results.append((src_path, cat))
        logger.info("Scanned %s -> found %d files", source_dir, len(results))
        return results

    @staticmethod
    def preview_files(files: list[tuple[Path, str]], temp_dir: Path) -> None:
        """Makes preview."""
        os.makedirs(temp_dir, exist_ok=True)
        for src, _ in files:
            dst = temp_dir / src.name
            try:
                # Symbolic link
                os.symlink(src, dst)
            except (OSError, NotImplementedError):
                try:
                    # hardlink
                    os.link(src, dst)
                except (OSError, NotImplementedError):
                    # Copy
                    shutil.copy2(src, dst)

    @staticmethod
    def collect_selected_files(
        files_to_process: list[tuple[Path, str]],
        target_dir: Path,
        dry_run: bool,
        update_status: Callable[[str], None],
        update_progress: Callable[[int], None],
    ) -> tuple[int, int, Path]:
        """Copies files with deduplication and report."""
        hashes: dict[str, str] = {}
        copied, renamed = 0, 0
        log_entries: list[str] = []
        total = len(files_to_process) or 1
        start_time = time.time()

        for i, (src_path, category) in enumerate(files_to_process):
            # ETA
            elapsed = time.time() - start_time
            avg_per_file = elapsed / (i + 1)
            remaining = avg_per_file * (total - i - 1)
            eta_str = time.strftime("%Mm %Ss", time.gmtime(remaining))

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

        # Log
        if not dry_run:
            os.makedirs(target_dir, exist_ok=True)
        run_log_path = target_dir / "log.txt"
        with open(run_log_path, "w", encoding="utf-8") as f:
            f.write(f"Run log at: {datetime.now()}\n")
            f.write("\n".join(log_entries))
            f.write(f"\n\nFiles copied: {copied}\nDuplicates renamed: {renamed}\n")

        return copied, renamed, target_dir


# =====================================================
# GUI
# =====================================================
class SummaryWindow(ctk.CTkToplevel):
    def __init__(self, parent, copied, renamed, target_dir, dry_run):
        super().__init__(parent)
        self.title("Summary")
        self.geometry("520x340")
        self.grab_set()

        status = "🧪 DRY RUN: No files copied.\n\n" if dry_run else "✅ DONE\n\n"
        msg = f"{status}Unique files: {copied}\nDuplicates: {renamed}\nDestination:\n{target_dir}"

        ctk.CTkLabel(self, text=msg, justify="left", wraplength=500).pack(pady=20)
        if not dry_run:
            ctk.CTkButton(self, text="📂 Open Folder", command=lambda: webbrowser.open(str(target_dir))).pack(pady=5)
        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=5)


class FileCollectorLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Universal File Collector")
        self.geometry("750x660")
        self.minsize(650, 500)

        ctk.CTkLabel(self, text="🔍 What do you want to collect?", font=("Segoe UI", 20, "bold")).pack(pady=(20, 5))

        self.options: dict[str, ctk.BooleanVar] = {}
        self._build_checkboxes()

        self.dry_run_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Dry run (simulate only)", variable=self.dry_run_var).pack(pady=(10, 0))

        self.skip_preview_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Skip Preview", variable=self.skip_preview_var).pack(pady=(5, 10))

        ctk.CTkButton(self, text="📁 Select Folder", command=self.select_folder, corner_radius=10).pack(pady=15)

        self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 14))
        self.status_label.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, height=14)
        self.progress.set(0)
        self.progress.pack(pady=10, fill="x", padx=20)

    def _build_checkboxes(self):
        frame = ctk.CTkFrame(self)
        frame.pack(pady=5, padx=20, fill="x")
        frame.grid_columnconfigure((0, 1), weight=1)

        var_all = ctk.BooleanVar()
        ctk.CTkCheckBox(frame, text="All", variable=var_all, command=self.toggle_all).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=2)
        self.options["All"] = var_all

        for idx, cat in enumerate(FILE_TYPES):
            var = ctk.BooleanVar()
            self.options[cat] = var
            ctk.CTkCheckBox(frame, text=cat, variable=var).grid(
                row=(idx // 2) + 1, column=idx % 2, sticky="w", padx=20, pady=2)

    def toggle_all(self):
        all_val = self.options["All"].get()
        for cat in FILE_TYPES:
            self.options[cat].set(all_val)

    def update_status_safe(self, text: str):
        self.after(0, lambda: self.status_label.configure(text=text))

    def update_progress_safe(self, val: int):
        self.after(0, lambda: self.progress.set(val / 100))

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder to scan")
        if not folder:
            return

        selected = [k for k, v in self.options.items() if v.get()]
        dry_run = self.dry_run_var.get()
        skip_preview = self.skip_preview_var.get()
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_dir = Path.home() / "Desktop" / f"COLLECTED_FILES_{now}"

        self.update_status_safe("Scanning for files...")

        def worker():
            try:
                files = FileCollectorCore.scan_files(folder, selected)
                self.update_status_safe(f"Found {len(files)} files.")
                self.update_progress_safe(0)

                if not files:
                    return

                if skip_preview:
                    self.run_copy(files, target_dir, dry_run)
                else:
                    temp_dir = Path(tempfile.gettempdir()) / f"TEMP_SCAN_{now}"
                    FileCollectorCore.preview_files(files, temp_dir)

                    def ask_user():
                        if messagebox.askyesno("Preview Files?",
                                               f"{len(files)} files found.\nPreview in Explorer?"):
                            webbrowser.open(str(temp_dir))
                            messagebox.showinfo("Continue", "Click OK to proceed.")
                        refreshed = [(f, FileCollectorCore.categorize_file(f)) for f in temp_dir.iterdir() if f.is_file()]
                        self.run_copy(refreshed, target_dir, dry_run)

                    self.after(100, ask_user)

            except Exception as e:
                logger.exception("Error during scan: %s", e)
                messagebox.showerror("Error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def run_copy(self, files, target_dir: Path, dry_run: bool):
        def run():
            try:
                copied, renamed, target = FileCollectorCore.collect_selected_files(
                    files, target_dir, dry_run, self.update_status_safe, self.update_progress_safe
                )
                self.update_status_safe(f"Done! Files: {copied}, Duplicates: {renamed}")
                self.update_progress_safe(100)
                self.after(100, lambda: SummaryWindow(self, copied, renamed, target, dry_run))
            except Exception as e:
                logger.exception("Error during processing: %s", e)
                messagebox.showerror("Error", str(e))

        threading.Thread(target=run, daemon=True).start()


# =====================================================
# Main
# =====================================================
if __name__ == "__main__":
    app = FileCollectorLauncher()
    app.mainloop()
