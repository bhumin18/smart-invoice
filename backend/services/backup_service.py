"""Backup and restore service for local SQLite deployments."""

from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from flask import send_file

from config import CONFIG_PATH, DATABASE_ENGINE
from utils.helpers import BACKUPS_OUTPUT_DIR, DATABASE_PATH, OUTPUT_DIR, ValidationError, ensure_directories, now_iso


logger = logging.getLogger(__name__)


def create_backup() -> str:
    """Create a zip backup of SQLite database, outputs, and YAML config."""
    if DATABASE_ENGINE != "sqlite":
        raise ValidationError({"database": "Backup export currently supports the SQLite adapter only"})
    ensure_directories()
    stamp = now_iso().replace(":", "-")
    backup_path = BACKUPS_OUTPUT_DIR / f"smart_invoice_backup_{stamp}.zip"
    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if DATABASE_PATH.exists():
            archive.write(DATABASE_PATH, "database/db.sqlite3")
        if CONFIG_PATH.exists():
            archive.write(CONFIG_PATH, "config.yaml")
        if OUTPUT_DIR.exists():
            for file_path in OUTPUT_DIR.rglob("*"):
                if file_path.is_file() and BACKUPS_OUTPUT_DIR not in file_path.parents:
                    archive.write(file_path, file_path.relative_to(OUTPUT_DIR.parent))
    logger.info("Created backup %s", backup_path)
    return str(backup_path)


def download_backup():
    """Return a fresh backup zip as a Flask download."""
    path = create_backup()
    return send_file(path, as_attachment=True, download_name=Path(path).name)


def restore_backup(uploaded_file: Any) -> dict[str, Any]:
    """Restore database and outputs from a backup zip file."""
    if DATABASE_ENGINE != "sqlite":
        raise ValidationError({"database": "Backup restore currently supports the SQLite adapter only"})
    if uploaded_file is None or not uploaded_file.filename:
        raise ValidationError({"backup": "Backup zip file is required"})
    if not str(uploaded_file.filename).lower().endswith(".zip"):
        raise ValidationError({"backup": "Backup must be a .zip file"})

    ensure_directories()
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "backup.zip"
        extract_dir = Path(tmp_dir) / "extract"
        uploaded_file.save(zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            bad_file = archive.testzip()
            if bad_file:
                raise ValidationError({"backup": f"Backup zip is corrupted at {bad_file}"})
            archive.extractall(extract_dir)

        restored: list[str] = []
        source_db = extract_dir / "database" / "db.sqlite3"
        if source_db.exists():
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_db, DATABASE_PATH)
            restored.append("database")

        source_outputs = extract_dir / "outputs"
        if source_outputs.exists():
            for child in source_outputs.iterdir():
                if child.name == "backups":
                    continue
                target = OUTPUT_DIR / child.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                if child.is_dir():
                    shutil.copytree(child, target)
                else:
                    shutil.copy2(child, target)
            restored.append("outputs")

    logger.warning("Restored backup sections: %s", ", ".join(restored) or "none")
    return {"restored": restored, "message": "Restart backend after restore for best consistency"}
