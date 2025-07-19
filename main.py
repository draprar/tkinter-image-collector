import os
import shutil
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog
import threading
import hashlib
import webbrowser

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

FILE_TYPES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"},
    "Documents": {".pdf", ".docx", ".txt", ".xlsx", ".csv", ".pptx"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
}


def file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_date_folder(path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    except Exception:
        return "no_dates"


def get_unique_name(base_path, filename, suffix=""):
    name, ext = os.path.splitext(filename)
    candidate = Path(base_path) / f"{name}{suffix}{ext}"
    i = 1
    while candidate.exists():
        candidate = Path(base_path) / f"{name}{suffix}_{i}{ext}"
        i += 1
    return candidate


def scan_files(source_dir, selected_types):
    all_exts = set.union(*(FILE_TYPES[t] for t in selected_types if t in FILE_TYPES)) if selected_types else set()
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
    hashes = {}
    copied = 0
    renamed = 0
    log = []
    total = len(files_to_process)

    for i, (src_path, category) in enumerate(files_to_process):
        update_progress(int((i + 1) / total * 100))
        update_status(f"Copying {src_path.name} ({i+1}/{total})")

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
            for line in log:
                f.write(line + "\n")
            f.write(f"\nFiles processed: {copied}\nDuplicates renamed: {renamed}\n")

    return copied, renamed, target_dir


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, files, target_dir, dry_run, update_status, update_progress):
        super().__init__(parent)
        self.title("Preview - Select Files to Process")
        self.geometry("700x500")
        self.grab_set()
        self.files = files
        self.vars = []

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for fpath, ftype in files:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(scroll_frame, text=f"[{ftype}] {fpath.name}", variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            self.vars.append((var, (fpath, ftype)))

        ctk.CTkButton(self, text="✅ Start", command=lambda: self.start_copy(parent, target_dir, dry_run, update_status, update_progress)).pack(pady=10)

    def start_copy(self, parent, target_dir, dry_run, update_status, update_progress):
        selected = [info for var, info in self.vars if var.get()]
        self.destroy()
        parent.run_copy(selected, target_dir, dry_run, update_status, update_progress)



class SummaryWindow(ctk.CTkToplevel):
    def __init__(self, parent, copied, renamed, target_dir, dry_run):
        super().__init__(parent)
        self.title("Summary")
        self.geometry("500x300")
        self.grab_set()

        if dry_run:
            preface = "🧪 DRY RUN MODE: No files were actually copied.\n\n"
        else:
            preface = "✅ OPERATION COMPLETE\n\n"

        msg = (
            f"{preface}"
            f"Unique files copied: {copied}\n"
            f"Duplicates renamed: {renamed}\n"
            f"Destination folder:\n{target_dir}"
        )

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
        option_frame = ctk.CTkFrame(self)
        option_frame.pack(pady=5, padx=20, fill="x")
        option_frame.grid_columnconfigure((0, 1), weight=1)

        var_all = ctk.BooleanVar()
        cb_all = ctk.CTkCheckBox(option_frame, text="All (collect everything)", variable=var_all, command=self.toggle_all)
        cb_all.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=2)
        self.options["All"] = var_all

        for idx, cat in enumerate(FILE_TYPES):
            var = ctk.BooleanVar()
            cb = ctk.CTkCheckBox(option_frame, text=cat, variable=var)
            cb.grid(row=(idx // 2) + 1, column=idx % 2, sticky="w", padx=20, pady=2)
            self.options[cat] = var

        self.dry_run_var = ctk.BooleanVar()
        ctk.CTkCheckBox(self, text="Dry run (simulate only)", variable=self.dry_run_var).pack(pady=(10, 0))

        self.select_button = ctk.CTkButton(self, text="📁 Select Folder and Preview", command=self.select_folder, corner_radius=10)
        self.select_button.pack(pady=15)

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, height=10)
        self.progress.set(0)
        self.progress.pack(pady=10, fill="x", padx=20)

    def toggle_all(self):
        all_val = self.options["All"].get()
        for k in FILE_TYPES:
            self.options[k].set(all_val)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder to scan")
        if not folder:
            return

        selected = [k for k, v in self.options.items() if v.get()]
        dry_run = self.dry_run_var.get()
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        desktop = Path.home() / "Desktop"
        target_dir = desktop / f"COLLECTED_FILES_{now}"

        self.status_label.configure(text="Scanning for files...")
        self.update_idletasks()

        def scan_and_preview():
            files = scan_files(folder, selected)
            self.status_label.configure(text=f"Found {len(files)} files to preview.")
            self.progress.set(0)
            self.after(100, lambda: PreviewWindow(self, files, target_dir, dry_run, self.status_label.configure, lambda v: self.progress.set(v / 100)))

        threading.Thread(target=scan_and_preview).start()

    def run_copy(self, selected_files, target_dir, dry_run, update_status, update_progress):
        def run():
            copied, renamed, target = collect_selected_files(
                selected_files, target_dir,
                dry_run, update_status, update_progress
            )
            update_status(f"Done! Files: {copied}, Duplicates: {renamed}")
            self.progress.set(1)
            self.after(100, lambda: SummaryWindow(self, copied, renamed, target, dry_run))

        threading.Thread(target=run).start()


if __name__ == "__main__":
    app = FileCollectorLauncher()
    app.mainloop()
