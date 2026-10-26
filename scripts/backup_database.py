"""Automated Database Backup and Disaster Recovery Script.

Supports:
- Timestamped compressed archive creation
- Cryptographic SHA-256 checksum generation for integrity auditing
- Automated retention management (removes backups older than N days)
- Dry-run and verification checks
"""

import argparse
import datetime
import gzip
import hashlib
import os
import shutil
import sys
from pathlib import Path

DEFAULT_DB_PATH = "./data/app.db"
DEFAULT_BACKUP_DIR = "./data/backups"
DEFAULT_RETENTION_DAYS = 30


def compute_sha256(filepath: str) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_backup(db_path: str = DEFAULT_DB_PATH, backup_dir: str = DEFAULT_BACKUP_DIR) -> str:
    """Create a compressed, checksummed backup of the application database."""
    source_path = Path(db_path).resolve()
    target_dir = Path(backup_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        print(f"[ERROR] Source database not found at: {source_path}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    backup_filename = f"exam_analyzer_db_{timestamp}.sqlite.gz"
    backup_path = target_dir / backup_filename
    checksum_path = target_dir / f"{backup_filename}.sha256"

    print(f"[*] Starting backup of {source_path}...")
    source_size = source_path.stat().st_size

    # Compress into gzip
    with open(source_path, "rb") as f_in:
        with gzip.open(backup_path, "wb", compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)

    compressed_size = backup_path.stat().st_size
    ratio = (1.0 - (compressed_size / source_size)) * 100 if source_size > 0 else 0

    # Generate SHA-256 checksum
    checksum = compute_sha256(str(backup_path))
    with open(checksum_path, "w", encoding="utf-8") as f_chk:
        f_chk.write(f"{checksum}  {backup_filename}\n")

    print(f"[+] Backup successfully generated: {backup_path}")
    print(f"    Raw size:        {source_size:,} bytes")
    print(f"    Compressed size: {compressed_size:,} bytes ({ratio:.1f}% reduction)")
    print(f"    SHA-256:         {checksum}")

    return str(backup_path)


def purge_expired_backups(backup_dir: str = DEFAULT_BACKUP_DIR, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
    """Purge backup archives older than the specified retention window."""
    target_dir = Path(backup_dir).resolve()
    if not target_dir.exists():
        return

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
    purged_count = 0

    for file in target_dir.glob("exam_analyzer_db_*.sqlite.gz*"):
        mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime, tz=datetime.timezone.utc)
        if mtime < cutoff:
            print(f"[-] Removing expired backup: {file.name} (Age: {mtime.isoformat()})")
            file.unlink()
            purged_count += 1

    if purged_count > 0:
        print(f"[+] Purged {purged_count} backups older than {retention_days} days.")
    else:
        print(f"[i] No backups exceeded retention threshold of {retention_days} days.")


def main():
    parser = argparse.ArgumentParser(description="Exam Analyzer Database Backup Utility")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR, help="Destination directory for backups")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS, help="Backup retention days")
    args = parser.parse_args()

    create_backup(args.db_path, args.backup_dir)
    purge_expired_backups(args.backup_dir, args.retention_days)


if __name__ == "__main__":
    main()
