import os
import shutil
import tempfile
import threading
import hashlib
import webbrowser
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

# --- UI Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# --- Supported File Types ---
FILE_TYPES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"},
    "Documents": {".pdf", ".docx", ".txt", ".xlsx", ".csv", ".pptx"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
}


# --- Utility Functions ---

def file_hash(filepath):
    """Calculate SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_date_folder(path):
    """Return formatted modification date for grouping."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    except Exception:
        return "no_dates"


def get_unique_name(base_path, filename, suffix=""):
    """Return unique filename by appending suffix and counter if needed."""
    name, ext = os.path.splitext(filename)
    candidate = Path(base_path) / f"{name}{suffix}{ext}"
    i = 1
    while candidate.exists():
        candidate = Path(base_path) / f"{name}{suffix}_{i}{ext}"
        i += 1
    return candidate


def scan_files(source_dir, selected_types):
    """Walk through directory tree and match files by selected types."""
    all_files = [Path(root) / f for root, _, files in os.walk(source_dir) for f in files]
    results = []

    for src_path in all_files:
        ext = src_path.suffix.lower()
        matched = None
        for category, ext_set in FILE_TYPES.items():
            if ext in ext_set and (category in selected_types or "All" in selected_types):
                matched = category
                break
        if not matched and "All" not in selected_types:
            continue
        results.append((src_path, matched or "OTHER"))
    return results


def collect_selected_files(files_to_process, target_dir, dry_run, update_status, update_progress):
    """Copy and deduplicate selected files into structured folders."""
    hashes = {}
    copied, renamed = 0, 0
    log = []
    total = len(files_to_process)

    for i, (src_path, category) in enumerate(files_to_process):
        update_progress(int((i + 1) / total * 100))
        update_status(f"Copying {src_path.name} ({i + 1}/{total})")

        file_h = file_hash(src_path)
        date_folder = get_date_folder(src_path)
        target_subdir = target_dir / f"{category}_{date_folder}"

        if not dry_run:
            os.makedirs(target_subdir, exist_ok=True)

        if file_h in hashes:
            new_dst = get_unique_name(target_subdir, src_path.name, suffix="_dup")
            log.append(f"DUPLICATE: {src_path} -> {new_dst.relative_to(target_dir)}")
            if not dry_run:
                shutil.copy2(src_path, new_dst)
            renamed += 1
            continue

        dst_path = get_unique_name(target_subdir, src_path.name)
        if dst_path.name != src_path.name:
            log.append(f"RENAME: {src_path.name} -> {dst_path.relative_to(target_dir)}")
            renamed += 1
        else:
            log.append(f"COPY: {src_path.name} -> {dst_path.relative_to(target_dir)}")

        if not dry_run:
            shutil.copy2(src_path, dst_path)
        hashes[file_h] = dst_path.name
        copied += 1

    if not dry_run:
        log_path = target_dir / "log.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Log generated at: {datetime.now()}\n")
            f.writelines(line + "\n" for line in log)
            f.write(f"\nFiles processed: {copied}\nDuplicates renamed: {renamed}\n")

    return copied, renamed, target_dir


# --- GUI Classes ---

class SummaryWindow(ctk.CTkToplevel):
    def __init__(self, parent, copied, renamed, target_dir, dry_run):
        super().__init__(parent)
        self.title("Summary")
        self.geometry("500x300")
        self.grab_set()

        status = "🧪 DRY RUN MODE: No files were actually copied.\n\n" if dry_run else "✅ OPERATION COMPLETE\n\n"
        msg = f"{status}Unique files copied: {copied}\nDuplicates renamed: {renamed}\nDestination folder:\n{target_dir}"

        ctk.CTkLabel(self, text=msg, justify="left", wraplength=480).pack(pady=20)

        if not dry_run:
            ctk.CTkButton(self, text="📂 Open Folder", command=lambda: webbrowser.open(str(target_dir))).pack(pady=5)

        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=5)


class FileCollectorLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Universal File Collector")
        self.geometry("700x550")
        self.minsize(600, 500)

        ctk.CTkLabel(self, text="🔍 What do you want to collect?", font=("Segoe UI", 18, "bold")).pack(pady=(20, 5))

        self.options = {}
        self._build_checkboxes()

        self.dry_run_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Dry run (simulate only)", variable=self.dry_run_var).pack(pady=(10, 0))

        ctk.CTkButton(self, text="📁 Select Folder", command=self.select_folder, corner_radius=10).pack(pady=15)

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, height=10)
        self.progress.set(0)
        self.progress.pack(pady=10, fill="x", padx=20)

    def _build_checkboxes(self):
        option_frame = ctk.CTkFrame(self)
        option_frame.pack(pady=5, padx=20, fill="x")
        option_frame.grid_columnconfigure((0, 1), weight=1)

        var_all = ctk.BooleanVar()
        ctk.CTkCheckBox(option_frame, text="All (collect everything)", variable=var_all, command=self.toggle_all).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=2)
        self.options["All"] = var_all

        for idx, cat in enumerate(FILE_TYPES):
            var = ctk.BooleanVar()
            self.options[cat] = var
            ctk.CTkCheckBox(option_frame, text=cat, variable=var).grid(
                row=(idx // 2) + 1, column=idx % 2, sticky="w", padx=20, pady=2)

    def toggle_all(self):
        all_val = self.options["All"].get()
        for cat in FILE_TYPES:
            self.options[cat].set(all_val)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder to scan")
        if not folder:
            return

        selected = [k for k, v in self.options.items() if v.get()]
        dry_run = self.dry_run_var.get()
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_dir = Path.home() / "Desktop" / f"COLLECTED_FILES_{now}"

        self.status_label.configure(text="Scanning for files...")
        self.update_idletasks()

        def scan_and_prompt():
            try:
                files = scan_files(folder, selected)
                self.status_label.configure(text=f"Found {len(files)} files.")
                self.progress.set(0)

                if not files:
                    return

                temp_dir = Path(tempfile.gettempdir()) / f"TEMP_SCAN_{now}"
                os.makedirs(temp_dir, exist_ok=True)
                for src, _ in files:
                    shutil.copy2(src, temp_dir)

                self.temp_dir = temp_dir

                def ask_user():
                    try:
                        if messagebox.askyesno("Preview Files?",
                                               f"{len(files)} files found.\n\nDo you want to preview them in Explorer?"):
                            webbrowser.open(str(temp_dir))
                            messagebox.showinfo("Continue?", "When you're done previewing, click OK to continue.")

                        refreshed_files = []
                        for f in temp_dir.iterdir():
                            if f.is_file():
                                ext = f.suffix.lower()
                                matched = next((cat for cat, exts in FILE_TYPES.items() if ext in exts), "OTHER")
                                refreshed_files.append((f, matched))

                        self.run_copy(refreshed_files, target_dir, dry_run,
                                      self.status_label.configure,
                                      lambda v: self.progress.set(v / 100))
                    except Exception as e:
                        print(f"[Error] During preview/refresh: {e}")
                        messagebox.showerror("Error", f"An error occurred: {e}")

                self.after(100, ask_user)

            except Exception as e:
                print(f"[Error] During scanning: {e}")
                messagebox.showerror("Error", f"An error occurred while scanning:\n{e}")

        threading.Thread(target=scan_and_prompt).start()

    def run_copy(self, selected_files, target_dir, dry_run, update_status, update_progress):
        def run():
            try:
                copied, renamed, target = collect_selected_files(
                    selected_files, target_dir, dry_run, update_status, update_progress
                )
                update_status(f"Done! Files: {copied}, Duplicates: {renamed}")
                self.progress.set(1)
                self.after(100, lambda: SummaryWindow(self, copied, renamed, target, dry_run))

                try:
                    if hasattr(self, "temp_dir") and self.temp_dir.exists():
                        shutil.rmtree(self.temp_dir)
                except Exception as cleanup_err:
                    print(f"[Warning] Failed to remove temp folder: {cleanup_err}")

            except Exception as e:
                print(f"[Error] During file processing: {e}")
                messagebox.showerror("Error", f"An error occurred during file processing:\n{e}")

        threading.Thread(target=run).start()


# --- Launch App ---
if __name__ == "__main__":
    app = FileCollectorLauncher()
    app.mainloop()
