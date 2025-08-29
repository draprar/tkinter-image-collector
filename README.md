# 📂 Universal File Collector

A modern cross-platform GUI tool that recursively scans a selected folder, collects files by chosen categories (Images, Documents, Videos, Audio, Archives, Other), and organizes them into categorized, date-based subfolders on your Desktop.

---

## ✅ Features

- Recursively scans all subfolders  
- Selectable file categories: **Images**, **Documents**, **Videos**, **Audio**, **Archives**, **Other**, or **All**  
- Organizes files into subfolders by **category** and **modification date** (`YYYY-MM-DD`)  
- Detects duplicate content using **SHA-256 hashing**  
- Renames duplicates by appending a suffix (`_dup`, `_dup1`, etc.) instead of skipping or overwriting  
- **Dry Run** mode simulates the entire process without modifying files or folders  
- Responsive GUI built with `customtkinter` featuring:  
  - Checkboxes for selecting file categories  
  - Status label and progress bar with ETA  
  - Preview window showing found files before final copying  
  - Summary dialog after operation completion  
- Creates `log.txt` with detailed file copy and rename operations (except in dry runs)  
- Supports manual preview of found files in Explorer (or system file manager)

---

## 📁 Supported formats

- **Images:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`  
- **Documents:** `.pdf`, `.docx`, `.txt`, `.xlsx`, `.csv`, `.pptx`  
- **Videos:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.3gp`, `.wmv`, `.m4v`  
- **Audio:** `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`  
- **Archives:** `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.iso`  
- **Other:** Files with unknown or unlisted extensions when **All** categories are selected

---

## 🧪 Dry Run Mode

- No actual file copying or folder creation  
- Detects duplicates and simulates renaming but does not modify files  
- Provides a preview of actions and expected results  
- No `log.txt` is written during dry run  

Use this mode to safely test how the operation would perform.

---

## 🚀 How to run

Install dependencies:

```
pip install -r requirements.txt
```

Run the script:
```
python main.py
```

---

## 🗂️ Output

- Output folder:  
  Created on your **Desktop** with a timestamp, e.g.:  
  `COLLECTED_FILES_2025-07-22_16-45-10`

- Inside:
  - Subfolders: named `<Category>_<YYYY-MM-DD>`  
    (e.g., `Documents_2025-06-30`, based on **file modification date**)  
  - Unique files are copied as-is  
  - Duplicate files (same content) are renamed with `_dup` suffix  
    (e.g., `report_dup.pdf`)  
  - A `log.txt` is generated (except in dry run), containing:
    - All copy and rename operations
    - Summary: number of copied files and renamed duplicates

---

## 📌 Example use case

You're recovering files from a messy backup or external drive and want to:
- Select only images and documents
- Sort them into clean folders by date and type
- Avoid overwriting duplicates (rename them instead)
- Preview everything in a temp folder before copying
- Get a clean, timestamped log of what happened

---

## 🗒️ Notes

- No original files are ever deleted or modified  
- Sorting is based only on **modification timestamps**  
- GUI gives real-time progress bar and status updates  
- All core file logic is covered by unit tests using `pytest`  
- Dry Run mode is perfect for safe previews  

---

![Tests](https://github.com/draprar/tkinter-image-collector/actions/workflows/ci.yml/badge.svg)