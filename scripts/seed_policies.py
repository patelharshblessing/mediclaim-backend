# scripts/seed_policies.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app import database_schema as models
from app.data.master_data import POLICY_RULEBOOK

def seed_policies():
    db = SessionLocal()
    try:
        print("Seeding policies into the database...")

        existing_policies = {p.policy_id for p in db.query(models.Policy).all()}

        for policy_id, policy_data in POLICY_RULEBOOK.items():
            if policy_id in existing_policies:
                print(f"Policy '{policy_id}' already exists. Skipping.")
                continue

            new_policy = models.Policy(
                policy_id=policy_id,
                policy_name=policy_data["policy_name"],
                rules=policy_data # SQLAlchemy will automatically handle the dict -> JSONB conversion
            )
            db.add(new_policy)
            print(f"Adding policy: {policy_id} - {policy_data['policy_name']}")

        db.commit()
        print("✅ Policies seeded successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_policies()