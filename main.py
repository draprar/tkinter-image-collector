import hashlib
import logging
import logging.handlers
import os
import shutil
import tempfile
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
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

# Constants
LOG_MAX_MB = 5
LOG_BACKUPS = 3
HASH_CHUNK_SIZE = 8192
DEFAULT_DATE_FOLDER = "no_dates"


# =====================================================
# Logger
# =====================================================
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


# =====================================================
# Core logic
# =====================================================
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
            hasher = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(HASH_CHUNK_SIZE):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as exc:
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
        except Exception:
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
        for src, _ in files:
            dst = temp_dir / src.name
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


# =====================================================
# GUI
# =====================================================
class SummaryWindow(ctk.CTkToplevel):
    """Popup window showing summary of the run."""

    def __init__(self, parent, copied: int, renamed: int, target_dir: Path, dry_run: bool):
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
    """Main launcher window for the file collector app."""

    def __init__(self):
        super().__init__()
        self.title("Universal File Collector")
        self.geometry("780x720")
        self.minsize(650, 520)

        self.temp_preview_dir: Optional[Path] = None
        self.source_folder: Optional[str] = None
        self.target_folder: Optional[str] = None

        ctk.CTkLabel(self, text="🔍 What do you want to collect?", font=("Segoe UI", 20, "bold")).pack(pady=(20, 5))

        self.options: dict[str, ctk.BooleanVar] = {}
        self._build_checkboxes()

        self.dry_run_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Dry run (simulate only)", variable=self.dry_run_var).pack(pady=(10, 0))

        self.skip_preview_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Skip Preview", variable=self.skip_preview_var).pack(pady=(5, 10))

        # Buttons to select folders (widened source button)
        self.select_source_button = ctk.CTkButton(
            self,
            text="📁 Select Source Folder",
            command=self.select_source_folder,
            width=220
        )
        self.select_source_button.pack(pady=6)

        self.select_target_button = ctk.CTkButton(self, text="📂 Select Destination Folder", command=self.select_target_folder, width=220)
        self.select_target_button.pack(pady=6)

        # Start button
        self.start_button = ctk.CTkButton(self, text="▶ Start Scan & Copy", command=self.start_process, fg_color="#3874f2", width=220)
        self.start_button.pack(pady=12)

        # Status + progress
        self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 14))
        self.status_label.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, height=14)
        # Keep determinate mode by default and start at 0
        self.progress.set(0)
        self.progress.pack(pady=10, fill="x", padx=20)

        # Show selected folders
        self.folders_frame = ctk.CTkFrame(self)
        self.folders_frame.pack(pady=6, padx=12, fill="x")
        self.source_label = ctk.CTkLabel(self.folders_frame, text="Source: (not set)", anchor="w")
        self.source_label.pack(fill="x", padx=8, pady=2)
        self.dest_label = ctk.CTkLabel(self.folders_frame, text="Destination: (not set)", anchor="w")
        self.dest_label.pack(fill="x", padx=8, pady=2)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_checkboxes(self) -> None:
        """Create category checkbox controls."""
        frame = ctk.CTkFrame(self)
        frame.pack(pady=5, padx=20, fill="x")
        frame.grid_columnconfigure((0, 1), weight=1)

        var_all = ctk.BooleanVar()
        ctk.CTkCheckBox(frame, text="All", variable=var_all, command=self.toggle_all).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=2
        )
        self.options["All"] = var_all

        for idx, cat in enumerate(FILE_TYPES):
            var = ctk.BooleanVar()
            self.options[cat] = var
            ctk.CTkCheckBox(frame, text=cat, variable=var).grid(
                row=(idx // 2) + 1, column=idx % 2, sticky="w", padx=20, pady=2
            )

    def toggle_all(self) -> None:
        """Toggle all category checkboxes based on 'All' control."""
        all_val = self.options["All"].get()
        for cat in FILE_TYPES:
            self.options[cat].set(all_val)

    def select_source_folder(self) -> None:
        """Ask user to select source folder to scan."""
        folder = filedialog.askdirectory(title="Select folder to scan")
        if folder:
            self.source_folder = folder
            self.source_label.configure(text=f"Source: {folder}")

    def select_target_folder(self) -> None:
        """Ask user to select destination folder."""
        folder = filedialog.askdirectory(title="Select destination folder")
        if folder:
            self.target_folder = folder
            self.dest_label.configure(text=f"Destination: {folder}")

    def update_status_safe(self, text: str) -> None:
        """Thread-safe UI status update."""
        self.after(0, lambda: self.status_label.configure(text=text))

    def update_progress_safe(self, val: int) -> None:
        """Thread-safe progress update (0-100)."""
        # val expected 0..100
        self.after(0, lambda: self.progress.set(val / 100))

    def start_process(self) -> None:
        """Validate inputs and start background worker to scan and copy files."""
        if not self.source_folder or not self.target_folder:
            messagebox.showerror("Error", "Please select both source and destination folders first.")
            return

        selected = [k for k, v in self.options.items() if v.get()]
        if not selected:
            messagebox.showerror("Error", "Please select at least one category (or All).")
            return

        # Disable UI controls
        self._disable_ui()
        # Ensure determinate progress and reset to 0
        self.progress.configure(mode="determinate")
        self.progress.set(0)
        self.update_status_safe("Preparing...")

        worker_args = {
            "selected": selected,
            "dry_run": self.dry_run_var.get(),
            "skip_preview": self.skip_preview_var.get(),
        }
        threading.Thread(target=self._worker_wrapper, args=(worker_args,), daemon=True).start()

    def _worker_wrapper(self, args: dict) -> None:
        """Background worker: scans, optionally previews, and runs copy."""
        selected = args["selected"]
        dry_run = args["dry_run"]
        skip_preview = args["skip_preview"]

        try:
            self.update_status_safe("Scanning for files...")
            files = FileCollectorCore.filter_files(self.source_folder, selected)
            # Keep determinate mode; progress will be driven by collect_selected_files
            self.after(0, lambda: self.progress.configure(mode="determinate"))
            self.update_status_safe(f"Found {len(files)} files.")
            self.update_progress_safe(0)

            if not files:
                messagebox.showinfo("Nothing found", "No files matched the selected categories.")
                self._enable_ui()
                return

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            target_root = Path(self.target_folder) / f"COLLECTED_FILES_{now}"

            if skip_preview:
                self._run_copy(files, target_root, dry_run)
            else:
                self.temp_preview_dir = Path(tempfile.gettempdir()) / f"TEMP_SCAN_{now}"
                FileCollectorCore.preview_files(files, self.temp_preview_dir)

                def ask_user_and_continue():
                    try:
                        if messagebox.askyesno("Preview Files?", f"{len(files)} files found.\nPreview in Explorer?"):
                            webbrowser.open(str(self.temp_preview_dir))
                            messagebox.showinfo("Continue", "Click OK to proceed.")
                        self._run_copy(files, target_root, dry_run)
                    except Exception as exc:
                        logger.exception("Error in preview flow: %s", exc)
                        messagebox.showerror("Error", str(exc))
                        self._enable_ui()

                self.after(100, ask_user_and_continue)

        except Exception as exc:
            logger.exception("Error during scan: %s", exc)
            messagebox.showerror("Error", str(exc))
            self._enable_ui()

    def _run_copy(self, files: list[tuple[Path, str]], target_root: Path, dry_run: bool) -> None:
        """Run the copy process in a separate thread and handle UI updates."""
        def run():
            try:
                copied, renamed, target = FileCollectorCore.collect_selected_files(
                    files, target_root, dry_run, self.update_status_safe, self.update_progress_safe
                )
                self.update_status_safe(f"Done! Files: {copied}, Duplicates: {renamed}")
                self.update_progress_safe(100)
                # Show summary window on main thread
                self.after(100, lambda: SummaryWindow(self, copied, renamed, target, dry_run))
            except Exception as exc:
                logger.exception("Error during processing: %s", exc)
                messagebox.showerror("Error", str(exc))
            finally:
                # cleanup preview dir if exists
                if self.temp_preview_dir and self.temp_preview_dir.exists():
                    try:
                        shutil.rmtree(self.temp_preview_dir, ignore_errors=True)
                        logger.debug("Removed temp preview dir %s", self.temp_preview_dir)
                        self.temp_preview_dir = None
                    except Exception:
                        logger.exception("Failed to remove temp preview dir %s", self.temp_preview_dir)
                self._enable_ui()

        threading.Thread(target=run, daemon=True).start()

    def _disable_ui(self) -> None:
        """Disable interactive UI elements while background work is running."""
        # disable only controls we know how to re-enable later
        try:
            self.start_button.configure(state="disabled")
            self.select_source_button.configure(state="disabled")
            self.select_target_button.configure(state="disabled")
            for k, v in self.options.items():
                # v is BooleanVar; find associated widget(s) by walking children
                # easiest: disable all checkboxes in the window
                pass
            # disable checkboxes by iterating all children (some are inside frames)
            for child in self.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        try:
                            if isinstance(sub, ctk.CTkCheckBox):
                                sub.configure(state="disabled")
                        except Exception:
                            pass
                else:
                    try:
                        if isinstance(child, ctk.CTkCheckBox):
                            child.configure(state="disabled")
                    except Exception:
                        pass
        except Exception:
            logger.exception("Failed to disable UI elements")

    def _enable_ui(self) -> None:
        """Re-enable UI elements after background work."""
        try:
            self.start_button.configure(state="normal")
            self.select_source_button.configure(state="normal")
            self.select_target_button.configure(state="normal")
            for child in self.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        try:
                            if isinstance(sub, ctk.CTkCheckBox):
                                sub.configure(state="normal")
                        except Exception:
                            pass
                else:
                    try:
                        if isinstance(child, ctk.CTkCheckBox):
                            child.configure(state="normal")
                    except Exception:
                        pass
        except Exception:
            logger.exception("Failed to enable UI elements")

    def on_close(self) -> None:
        """Cleanup temporary preview dir (if any) and close app."""
        if self.temp_preview_dir and self.temp_preview_dir.exists():
            try:
                shutil.rmtree(self.temp_preview_dir, ignore_errors=True)
            except Exception:
                logger.exception("Failed to remove temp preview dir %s on exit", self.temp_preview_dir)
        self.destroy()


# =====================================================
# Main
# =====================================================
if __name__ == "__main__":
    app = FileCollectorLauncher()
    app.mainloop()
