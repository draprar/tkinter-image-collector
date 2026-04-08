"""GUI components for file collection."""

import shutil
import tempfile
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import TclError, filedialog, messagebox
from typing import Any, Callable, Optional

import customtkinter as ctk

from core import FILE_TYPES, FileCollectorCore, logger

# Type alias
StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]


@dataclass(frozen=True)
class WorkerArgs:
    """Immutable arguments passed into the background worker."""

    selected: list[str]
    dry_run: bool
    skip_preview: bool


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

        # Configure UI theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("green")

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

        # Buttons to select folders
        self.select_source_button = ctk.CTkButton(
            self,
            text="📁 Select Source Folder",
            command=self.select_source_folder,
            width=220
        )
        self.select_source_button.pack(pady=6)

        self.select_target_button = ctk.CTkButton(
            self,
            text="📂 Select Destination Folder",
            command=self.select_target_folder,
            width=220
        )
        self.select_target_button.pack(pady=6)

        # Start button
        self.start_button = ctk.CTkButton(
            self,
            text="▶ Start Scan & Copy",
            command=self.start_process,
            fg_color="#3874f2",
            width=220
        )
        self.start_button.pack(pady=12)

        # Status + progress
        self.status_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 14))
        self.status_label.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, height=14)
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
        self.after(0, lambda: self.progress.set(val / 100))

    def _show_info_safe(self, title: str, message: str) -> None:
        """Show info dialog on main UI thread."""
        self.after(0, lambda: messagebox.showinfo(title, message))

    def _show_error_safe(self, title: str, message: str) -> None:
        """Show error dialog on main UI thread."""
        self.after(0, lambda: messagebox.showerror(title, message))

    def _enable_ui_safe(self) -> None:
        """Re-enable controls on main UI thread."""
        self.after(0, self._enable_ui)

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

        worker_args = WorkerArgs(
            selected=selected,
            dry_run=self.dry_run_var.get(),
            skip_preview=self.skip_preview_var.get(),
        )
        threading.Thread(target=self._worker_wrapper, args=(worker_args,), daemon=True).start()

    def _worker_wrapper(self, args: WorkerArgs) -> None:
        """Background worker: scans, optionally previews, and runs copy."""
        selected = args.selected
        dry_run = args.dry_run
        skip_preview = args.skip_preview

        try:
            if not self.source_folder:
                raise ValueError("Source folder must be selected before starting worker")
            if not self.target_folder:
                raise ValueError("Destination folder must be selected before starting worker")

            self.update_status_safe("Scanning for files...")
            files = FileCollectorCore.filter_files(self.source_folder, selected)
            self.after(0, lambda: self.progress.configure(mode="determinate"))
            self.update_status_safe(f"Found {len(files)} files.")
            self.update_progress_safe(0)

            if not files:
                self._show_info_safe("Nothing found", "No files matched the selected categories.")
                self._enable_ui_safe()
                return

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            target_root = Path(self.target_folder) / f"COLLECTED_FILES_{now}"

            if not dry_run:
                has_space, required_bytes, free_bytes = FileCollectorCore.check_disk_space(
                    target_root, files
                )
                if not has_space:
                    required_mb = required_bytes // (1024 * 1024)
                    free_mb = free_bytes // (1024 * 1024)
                    self._show_error_safe(
                        "Not enough disk space",
                        f"Need about {required_mb} MB but only {free_mb} MB is free.",
                    )
                    self._enable_ui_safe()
                    return

            if skip_preview:
                self._run_copy(files, target_root, dry_run)
            else:
                self.temp_preview_dir = Path(tempfile.gettempdir()) / f"TEMP_SCAN_{now}"
                FileCollectorCore.preview_files(files, self.temp_preview_dir)

                def ask_user_and_continue():
                    try:
                        if messagebox.askyesno("Preview Files?", f"{len(files)} files found.\nPreview in Explorer?"):
                            if self.temp_preview_dir:
                                webbrowser.open(str(self.temp_preview_dir))
                            messagebox.showinfo("Continue", "Click OK to proceed.")
                        self._run_copy(files, target_root, dry_run)
                    except (TclError, OSError, RuntimeError, ValueError) as exc:
                        logger.exception("Error in preview flow: %s", exc)
                        self._show_error_safe("Error", str(exc))
                        self._enable_ui_safe()

                self.after(100, ask_user_and_continue)

        except (TclError, OSError, RuntimeError, ValueError) as exc:
            logger.exception("Error during scan: %s", exc)
            self._show_error_safe("Error", str(exc))
            self._enable_ui_safe()

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
            except (TclError, OSError, RuntimeError, ValueError) as exc:
                logger.exception("Error during processing: %s", exc)
                self._show_error_safe("Error", str(exc))
            finally:
                # cleanup preview dir if exists
                if self.temp_preview_dir and self.temp_preview_dir.exists():
                    try:
                        shutil.rmtree(self.temp_preview_dir, ignore_errors=True)
                        logger.debug("Removed temp preview dir %s", self.temp_preview_dir)
                        self.temp_preview_dir = None
                    except OSError:
                        logger.exception("Failed to remove temp preview dir %s", self.temp_preview_dir)
                self._enable_ui_safe()

        threading.Thread(target=run, daemon=True).start()

    def _disable_ui(self) -> None:
        """Disable interactive UI elements while background work is running."""
        try:
            self.start_button.configure(state="disabled")
            self.select_source_button.configure(state="disabled")
            self.select_target_button.configure(state="disabled")
            self._set_checkboxes_state("disabled")
        except (TclError, AttributeError, RuntimeError):
            logger.exception("Failed to disable UI elements")

    def _enable_ui(self) -> None:
        """Re-enable UI elements after background work."""
        try:
            self.start_button.configure(state="normal")
            self.select_source_button.configure(state="normal")
            self.select_target_button.configure(state="normal")
            self._set_checkboxes_state("normal")
        except (TclError, AttributeError, RuntimeError):
            logger.exception("Failed to enable UI elements")

    def _set_checkboxes_state(self, state: str) -> None:
        """Recursively set state on all checkbox widgets in the window."""
        for widget in self.winfo_children():
            self._set_checkboxes_state_recursive(widget, state)

    def _set_checkboxes_state_recursive(self, widget: Any, state: str) -> None:
        """Traverse widget tree and update checkbox state."""
        if isinstance(widget, ctk.CTkCheckBox):
            widget.configure(state=state)
        for child in widget.winfo_children():
            self._set_checkboxes_state_recursive(child, state)

    def on_close(self) -> None:
        """Cleanup temporary preview dir (if any) and close app."""
        if self.temp_preview_dir and self.temp_preview_dir.exists():
            try:
                shutil.rmtree(self.temp_preview_dir, ignore_errors=True)
            except OSError:
                logger.exception("Failed to remove temp preview dir %s on exit", self.temp_preview_dir)
        self.destroy()

