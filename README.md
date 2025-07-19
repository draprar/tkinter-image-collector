# 📂 Universal File Collector

A modern GUI tool for Windows that recursively scans a selected folder, collects files by selected categories (Images, Documents, Videos, Audio, Archives), and saves them into organized directories on your Desktop.

---

## ✅ Features

- Recursively scans all subfolders  
- Supports selectable file categories: Images, Documents, Videos, Audio, Archives, or All  
- Copies selected file types to a new folder on the Desktop  
- Automatically organizes files into subfolders by category and date (file modification date)  
- Detects duplicates by **SHA256 hash**  
- Renames duplicates with `_dup` suffix instead of skipping  
- Displays progress bar and status updates in the GUI  
- Supports **Dry Run** mode (simulate without copying or renaming)  
- Generates a `log.txt` file with detailed operation records (except in dry run mode)  
- Simple, responsive customtkinter GUI with checkboxes for file type selection  
- Ability to open output folder directly from summary window  

---

## 📁 Supported formats

- **Images:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`  
- **Documents:** `.pdf`, `.docx`, `.txt`, `.xlsx`, `.csv`, `.pptx`  
- **Videos:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.3gp`, `.wmv`, `.m4v`  
- **Audio:** `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`  
- **Archives:** `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.iso`  

---

## 🧪 Dry Run Mode

When the checkbox **Dry run (simulate only)** is selected:  
- No files or folders are created  
- No copying or renaming occurs  
- The process simulates the entire operation and provides a summary  
- Useful for previewing results before actual changes  

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

- A new folder is created on your Desktop with a timestamped name, e.g., `COLLECTED_FILES_2025-07-15_15-30-00`  
- Inside the folder, files are organized into subfolders named `<Category>_<YYYY-MM-DD>`, based on file modification date  
- Duplicate files with identical content are renamed with a `_dup` suffix (e.g., `document_dup.pdf`)  
- A `log.txt` file is created in the root output folder (except in dry run mode)  
  - Contains detailed copy/rename/duplicate actions and a summary  

---

## 📌 Example use case

You want to recover and organize your files from a large, messy folder structure by:  
- Selecting exactly which file types to collect  
- Sorting files by category and modification date  
- Keeping all unique files intact and renaming duplicates  
- Previewing the process before actual copying with dry run mode  

---

## 🗒️ Notes

- The source files and folders are never deleted or modified  
- Sorting is based solely on file modification timestamps  
- The GUI provides real-time progress and status messages

---

![Tests](https://github.com/draprar/tkinter-image-collector/actions/workflows/ci.yml/badge.svg)