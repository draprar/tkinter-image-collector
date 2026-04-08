# Contributing

Thanks for taking the time to contribute.

## Quick start

1. Fork the repo and create a feature branch.
2. Install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run checks before opening a PR:

```powershell
pytest -q
ruff check .
mypy core.py ui.py main.py
python -m bandit -q core.py ui.py main.py
```

## PR guidelines

- Keep changes focused and well-scoped.
- Add or update tests for behavior changes.
- Update documentation if you change user-facing behavior.
- Ensure CI is green before requesting review.

