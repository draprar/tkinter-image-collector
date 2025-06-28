# Image Collector

This is a simple Python tool that recursively scans a user-selected folder and all its subfolders for image files, then copies all images into a new folder on your Desktop. It handles duplicate filenames and identical file contents by automatically renaming duplicates with suffixes like `_1` or `_dup`. 

A log file detailing all operations is saved in the new folder.

## Features

- Recursive search through all subfolders
- Supports common image formats: JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP
- Detects duplicates by file content (SHA256 hash) and renames them instead of skipping
- Creates a timestamped folder on the Desktop for collected images
- Generates a detailed log file with copy/rename operations
- Simple GUI for folder selection and user messages (using Tkinter)

## Requirements

- Python 3.8 or higher
- Tkinter (usually included in standard Python installs)
- No additional dependencies

## Usage

1. Run the script:
```
python main.py
```
3. An info window will explain the program.
3. Select the folder you want to scan.
4. The program will create a new folder on your Desktop with all collected images and a log file.
5. After completion, a summary window will appear.

## Notes

- Duplicate files with the same name or identical content are renamed automatically.
- The log file (`log.txt`) contains full details of copied and renamed files.

## License

This script is free to use and modify.

---

Enjoy organizing your image collections!
