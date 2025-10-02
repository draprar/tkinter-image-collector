# 📂 Universal File Collector

Windows GUI tool that hunts through messy folders, grabs your files by type (Images, Docs, Videos, Audio, Archives), and neatly drops them into timestamped folders on your Desktop.

---

## ✅ Features

- Recursively scans all subfolders  
- Selectable file categories: **Images**, **Documents**, **Videos**, **Audio**, **Archives**, or **All**  
- Automatically organizes files into subfolders by **category** and **modification date**  
- Detects **duplicate content** using **SHA-256 hashes**  
- Renames duplicates with `_dup` suffix instead of skipping or overwriting  
- **Dry Run** mode: simulate the operation without copying or modifying anything  
- Responsive `customtkinter` GUI with:
  - Category checkboxes
  - Status label and progress bar
  - Preview dialog before copying
  - Summary window with result info
- Creates `log.txt` with detailed file actions (only in real runs)
- Supports **manual preview** of found files via Explorer before final copy

---

## 📁 Supported formats

- **Images:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`  
- **Documents:** `.pdf`, `.docx`, `.txt`, `.xlsx`, `.csv`, `.pptx`  
- **Videos:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.3gp`, `.wmv`, `.m4v`  
- **Audio:** `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`  
- **Archives:** `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.iso`  

Files with unknown extensions are categorized under **`OTHER`** when "All" is selected.

---

## 🧪 Dry Run Mode

When **Dry run (simulate only)** is selected:
- No folders or files are created or copied  
- Duplicates are detected but not renamed  
- A full simulation is run to estimate results  
- Summary is shown without writing `log.txt`  

Use this to **preview what would happen** before committing to changes.

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
