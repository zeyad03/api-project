"""Database onboarding script – creates the admin user for the F1 Facts API.

Collections, indexes, and seed data are handled by the seed script
(``python -m src.data.seed``), which pulls from the Kaggle dataset.
This script only ensures the admin account exists so you can log in
immediately after onboarding.

Usage:
    python -m scripts.mongodb.onboard          # uses settings from .env
    MONGO_URI=mongodb://... python -m scripts.mongodb.onboard
"""

from pymongo.mongo_client import MongoClient

from src.config.settings import settings
from src.core.security import hash_password
from src.db.collections import collections
from src.models.common import utc_now

# ── Connect ──────────────────────────────────────────────────────────────────
client = MongoClient(settings.MONGO_URI)
db = client.get_database(settings.DB_NAME)

print(f"🔌  Connected to MongoDB: {settings.MONGO_URI}")
print(f"📂  Database: {settings.DB_NAME}\n")

# ── Create admin user ───────────────────────────────────────────────────────
admin = db[collections.users].find_one({"username": "admin"})

if admin:
    print("  ℹ️   Admin user already exists, skipping")
else:
    now = utc_now()
    db[collections.users].insert_one(
        {
            "username": "admin",
            "email": "admin@f1facts.api",
            "display_name": "Admin",
            "password_hash": hash_password("admin123"),
            "is_admin": True,
            "created_at": now,
        }
    )
    print("  ✅  Created admin user (username: admin, password: admin123)")

# ── Done ─────────────────────────────────────────────────────────────────────
client.close()
print("\n🏁  Onboarding complete!\n")
print("Next steps:")
print("  • Run 'make seed' to populate drivers, teams, and facts from Kaggle data")
print("  • Run 'make dev' to start the development server")
