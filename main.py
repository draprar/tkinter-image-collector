import os
import shutil
import hashlib
from tkinter import Tk, filedialog, messagebox
from pathlib import Path
from datetime import datetime

def file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_unique_name(base_path, filename, suffix=""):
    name, ext = os.path.splitext(filename)
    candidate = Path(base_path) / f"{name}{suffix}{ext}"
    i = 1
    while candidate.exists():
        candidate = Path(base_path) / f"{name}{suffix}_{i}{ext}"
        i += 1
    return candidate

def main():
    root = Tk()
    root.withdraw()

    # 🔲 Show intro window with instructions
    intro = (
        "🎯 This program scans the selected folder and all its subfolders,\n"
        "copies all image files to a new folder on your Desktop,\n"
        "adding appropriate tags to duplicate filenames (e.g., _1, _dup).\n\n"
        "📦 A new folder will be created containing a log file and all copied files.\n\n"
        "➡️ Click OK to choose the folder to scan."
    )
    messagebox.showinfo("Image Collector – Introduction", intro)

    # 📁 Select source directory
    source_dir = filedialog.askdirectory(title="Select folder to scan")
    if not source_dir:
        messagebox.showinfo("Cancelled", "No folder selected – exiting.")
        return

    # 📂 Create output folder
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    desktop = Path.home() / "Desktop"
    target_dir = desktop / f"COLLECTED_IMAGES_{now}"
    os.makedirs(target_dir, exist_ok=True)

    # 🔎 Settings
    log_path = target_dir / "log.txt"
    exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    hashes = {}
    copied = 0
    renamed = 0
    log = []

    # 🔁 Recursively scan the source folder
    for root, _, files in os.walk(source_dir):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in exts:
                continue

            src_path = Path(root) / filename
            file_h = file_hash(src_path)

            if file_h in hashes:
                new_dst = get_unique_name(target_dir, filename, suffix="_dup")
                log.append(f"DUPLICATE: {src_path} -> {new_dst.name}")
                shutil.copy2(src_path, new_dst)
                renamed += 1
                continue

            dst_path = get_unique_name(target_dir, filename)
            if dst_path.name != filename:
                log.append(f"RENAME: {src_path.name} -> {dst_path.name}")
                renamed += 1
            else:
                log.append(f"COPY: {src_path.name}")

            shutil.copy2(src_path, dst_path)
            hashes[file_h] = dst_path.name
            copied += 1

    # 📝 Save the log
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"📅 Log generated at: {datetime.now()}\n")
        f.write(f"Source folder: {source_dir}\nDestination folder: {target_dir}\n\n")
        for line in log:
            f.write(line + "\n")
        f.write(f"\n✅ Files copied: {copied}\n🪪 Filenames changed due to duplicates: {renamed}\n")

    # 📢 Summary message
    msg = f"📁 {copied} files copied to:\n{target_dir}\n\n"
    msg += f"🪪 {renamed} duplicate filenames/content were renamed\n"
    msg += f"📄 Log saved as log.txt"
    messagebox.showinfo("Done!", msg)

if __name__ == "__main__":
    main()
