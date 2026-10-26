"""Automated Database Restoration and Integrity Verification Utility."""

import argparse
import gzip
import hashlib
import os
import shutil
import sys
from pathlib import Path

DEFAULT_DB_PATH = "./data/app.db"


def compute_sha256(filepath: str) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def restore_backup(backup_path: str, target_db: str = DEFAULT_DB_PATH, skip_verify: bool = False) -> None:
    """Restore database from a gzip archive with optional SHA-256 validation."""
    archive_path = Path(backup_path).resolve()
    target_path = Path(target_db).resolve()

    if not archive_path.exists():
        print(f"[ERROR] Backup archive does not exist at: {archive_path}", file=sys.stderr)
        sys.exit(1)

    # Integrity verification
    checksum_file = archive_path.parent / f"{archive_path.name}.sha256"
    if checksum_file.exists() and not skip_verify:
        with open(checksum_file, "r", encoding="utf-8") as f:
            expected_hash = f.read().split()[0].strip()
        computed_hash = compute_sha256(str(archive_path))
        if computed_hash.lower() != expected_hash.lower():
            print(f"[SECURITY ALERT] Backup SHA-256 checksum mismatch!", file=sys.stderr)
            print(f"  Expected: {expected_hash}", file=sys.stderr)
            print(f"  Actual:   {computed_hash}", file=sys.stderr)
            sys.exit(2)
        print(f"[+] Backup integrity confirmed via SHA-256: {computed_hash}")

    # Create safety snapshot of existing active DB before overwrite
    if target_path.exists():
        safety_path = target_path.with_suffix(".pre_restore.bak")
        shutil.copy2(target_path, safety_path)
        print(f"[i] Stored pre-restoration safety snapshot at: {safety_path}")

    # Decompress and write to target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(archive_path, "rb") as f_in:
        with open(target_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"[SUCCESS] Database successfully restored to: {target_path} ({target_path.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Exam Analyzer Database Restoration Utility")
    parser.add_argument("backup_file", help="Path to .sqlite.gz backup archive")
    parser.add_argument("--target-db", default=DEFAULT_DB_PATH, help="Target SQLite DB destination")
    parser.add_argument("--skip-verify", action="store_true", help="Skip SHA-256 checksum check")
    args = parser.parse_args()

    restore_backup(args.backup_file, args.target_db, args.skip_verify)


if __name__ == "__main__":
    main()
