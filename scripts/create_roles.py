# scripts/create_roles.py
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.database_schema import Role


def create_initial_roles():
    db = SessionLocal()
    try:
        print("Checking and creating roles...")

        # --- Define the roles you need ---
        roles_to_create = ["admin", "claims_processor"]

        for role_name in roles_to_create:
            # Check if the role already exists
            existing_role = db.query(Role).filter(Role.role_name == role_name).first()
            if not existing_role:
                # If it doesn't exist, create it
                new_role = Role(role_name=role_name)
                db.add(new_role)
                print(f"  - Created role: '{role_name}'")
            else:
                print(f"  - Role '{role_name}' already exists. Skipping.")

        db.commit()
        print("✅ Roles are set up in the database.")

    finally:
        db.close()


if __name__ == "__main__":
    create_initial_roles()
