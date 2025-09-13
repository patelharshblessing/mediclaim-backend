import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_password_hash
from app.database import SessionLocal
from app.database_schema import Role, User

# def add_sample_user():
#     db = SessionLocal()
#     username = "testuser"
#     password = "testpassword"
#     hashed_password = get_password_hash(password)
#     user = User(
#         username=username,
#         hashed_password=hashed_password,
#         full_name="Test User",
#         email="testuser@example.com",
#         is_active=True
#     )
#     db.add(user)
#     db.commit()
#     db.refresh(user)
#     print(f"✅ Added user: {username} with password: {password}")
#     db.close()


def add_admin_user():
    """
    Creates a new user with the 'admin' role in the database.
    """
    db = SessionLocal()
    try:
        # --- Step 1: Find the 'admin' role ---
        admin_role = db.query(Role).filter(Role.role_name == "admin").first()

        if not admin_role:
            print("❌ Error: The 'admin' role was not found in the database.")
            print("Please run the initial data creation script first to create roles.")
            return

        # --- Step 2: Define the new admin user's details ---
        username = "superadmin"
        password = "supersecretpassword"

        # Check if the user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists. Skipping.")
            return

        # --- Step 3: Create and save the new user ---
        hashed_password = get_password_hash(password)
        new_admin = User(
            username=username,
            hashed_password=hashed_password,
            full_name="Super Administrator",
            email="superadmin@example.com",
            is_active=True,
            role_id=admin_role.role_id,  # Assign the admin role's ID
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        print(f"✅ Successfully added new admin user:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")

    finally:
        db.close()


if __name__ == "__main__":
    # add_sample_user()
    add_admin_user()
