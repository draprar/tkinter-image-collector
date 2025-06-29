# 📸 Image Collector

A modern GUI tool for Windows that recursively scans a selected folder, collects image files, and saves them into a single, organized directory on your Desktop.

---

## ✅ Features

- Recursively scans all subfolders
- Copies all image files to a new folder on the Desktop
- Automatically organizes images into subfolders by date (EXIF or file modification date)
- Detects duplicates by **SHA256 hash**
- Renames duplicates with `_dup` suffix instead of skipping
- Displays progress bar and status updates
- Supports **Dry Run** mode (no files are actually copied)
- Generates a `log.txt` file with operation details (except in dry run)

---

## 📁 Supported formats

- `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`

---

## 🧪 Dry Run Mode

When the checkbox **Dry run (simulate only)** is selected:
- No files or folders are created
- Nothing is copied or renamed
- A full simulation is performed and a summary is shown
- Useful for previewing the results without making changes

---

## 🚀 How to run

Install required packages:

```bash
pip install -r requirements.txt
````

Run the script:
```
python main.py
```

## 🗂️ Output

- A new folder is created on the Desktop: `COLLECTED_IMAGES_<timestamp>`
- Inside it, images are grouped into subfolders like `2024-07-01`, based on EXIF date or file modification date
- Duplicate images (same content) are renamed with a `_dup` suffix (e.g., `IMG_001_dup.jpg`)
- A `log.txt` file is created in the root output folder (unless running in dry run mode)
  - Contains paths and actions taken (`COPY`, `RENAME`, `DUPLICATE`)
  - Summary of number of copied and renamed files

---

## 🔧 Requirements

- Python 3.10 or newer
- Tested on Windows 10/11

---

## 📌 Example use case

You recovered data from a disk and want to:

- Scan a deeply nested directory
- Extract only image files
- Organize them by date
- Keep all unique files and rename duplicates with `_dup`

---

## 🗒️ Notes

- The app does not delete or modify any files in the source folder
- Sorting is based on EXIF date or file modification time
- Progress is shown during scanning and copying

---

MIT licensed.
