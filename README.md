# Universal File Collector

Desktop GUI tool for sorting files by type and modification date.
It scans a source directory recursively, groups files into categories,
detects duplicate content using SHA-256, and copies results into a timestamped
folder inside a destination directory chosen by the user.

## Features

- Recursive scan of source folder.
- Category filtering: `Images`, `Documents`, `Videos`, `Audio`, `Archives`, `All`.
- Organization by `<Category>_<YYYY-MM-DD>`.
- Duplicate content detection via SHA-256.
- Duplicate file renaming with `_dup` suffix (no overwrites).
- Optional preview step before copy.
- Dry-run mode with no filesystem writes to destination.
- Preflight disk-space check before real copy operation.
- Run summary in GUI and persistent `log.txt` for real runs.

## Supported formats

- `Images`: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`
- `Documents`: `.pdf`, `.docx`, `.txt`, `.xlsx`, `.csv`, `.pptx`
- `Videos`: `.mp4`, `.mov`, `.avi`, `.mkv`, `.3gp`, `.wmv`, `.m4v`
- `Audio`: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`
- `Archives`: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.iso`

Unknown extensions are categorized as `OTHER` when `All` is selected.

## Dry run behavior

When `Dry run (simulate only)` is enabled:

- no files are copied,
- destination subfolders are not created,
- `log.txt` is not written,
- summary is still displayed in GUI.

## Installation and run

Create and activate virtual environment (Windows PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run app:

```powershell
python main.py
```

## Dependency files

- `requirements-runtime.txt` - app runtime dependencies.
- `requirements-dev.txt` - test/lint/security tooling.
- `requirements-build.txt` - build-time dependencies.
- `requirements.txt` - convenience meta-file (runtime + dev).

## Module structure

- `core.py` — `FileCollectorCore` class (business logic, no UI dependencies).
- `ui.py` — `FileCollectorLauncher`, `SummaryWindow` (GUI components).
- `main.py` — Entry point (imports and runs UI).

This separation allows:
- Testing of core logic independently from GUI.
- Easier GUI refactoring (e.g., switch to PyQt later).
- Cleaner dependency management.

## Output structure

After selecting destination folder in GUI, app creates a run directory like:

`COLLECTED_FILES_2026-04-08_12-30-00`

Inside it:

- subfolders named `<Category>_<YYYY-MM-DD>`,
- copied unique files,
- renamed duplicates with `_dup`,
- `log.txt` (only for real runs).

## Quality checks

```powershell
pytest -q
ruff check .
mypy core.py ui.py main.py
bandit -q -r core.py -r ui.py -r main.py
pip-audit -r requirements-runtime.txt
```

Optional local hooks:

```powershell
pre-commit install
pre-commit run --all-files
```

## Author

Developed by Walery ([@draprar](https://github.com/draprar/))

![Tests](https://github.com/draprar/tkinter-image-collector/actions/workflows/ci.yml/badge.svg)
