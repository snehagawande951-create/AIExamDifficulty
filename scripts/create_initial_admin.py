"""CLI setup script to securely provision the initial system administrator.

Usage:
    python scripts/create_initial_admin.py --email admin@example.edu --name "Admin Name" --password "SecurePassword123!"
Or run interactively:
    python scripts/create_initial_admin.py
"""

import argparse
import getpass
import os
import sys

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.security import get_password_hash
from backend.app.db.session import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.models.audit import AuditEvent


def provision_admin(email: str, full_name: str, password: str) -> None:
    """Create the primary administrative account in the database."""
    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role == UserRole.ADMIN:
                print(f"[INFO] Administrator account '{email}' already exists.")
                return
            else:
                print(f"[WARNING] User '{email}' exists with role '{existing.role.value}'. Elevating to ADMIN...")
                existing.role = UserRole.ADMIN
                existing.is_active = True
                db.commit()
                print(f"[SUCCESS] User '{email}' elevated to ADMIN.")
                return

        hashed_password = get_password_hash(password)
        admin_user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            institution="System Administration",
            department="IT / Research Governance",
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        audit = AuditEvent(
            user_id=admin_user.id,
            action="INITIAL_ADMIN_PROVISIONED",
            resource_type="USER",
            resource_id=str(admin_user.id),
            details=f"Initial administrator {admin_user.email} provisioned via CLI",
        )
        db.add(audit)
        db.commit()

        print(f"[SUCCESS] Initial administrator created successfully!")
        print(f"  User ID : {admin_user.id}")
        print(f"  Email   : {admin_user.email}")
        print(f"  Role    : {admin_user.role.value}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Secure Initial Admin Provisioning Tool")
    parser.add_argument("--email", help="Administrator email address")
    parser.add_argument("--name", help="Administrator full name")
    parser.add_argument("--password", help="Administrator password")

    args = parser.parse_args()

    email = args.email or input("Enter administrator email: ").strip()
    full_name = args.name or input("Enter administrator full name: ").strip()
    
    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Enter administrator password: ")
        confirm_pass = getpass.getpass("Confirm administrator password: ")
        if password != confirm_pass:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    provision_admin(email, full_name, password)


if __name__ == "__main__":
    main()
