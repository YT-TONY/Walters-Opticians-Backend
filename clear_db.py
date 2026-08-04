import os
from sqlalchemy import MetaData
from app.db.session import engine
from app.db.base import Base

def clear_db():
    print("Clearing database...")

    # 1. Drop all tables using SQLAlchemy Metadata
    meta = MetaData()
    meta.reflect(bind=engine)
    meta.drop_all(bind=engine)
    print("✓ All database tables dropped successfully.")

    # 2. Re-create empty tables cleanly from your ORM models
    Base.metadata.create_all(bind=engine)
    print("✓ Fresh database schema created successfully.")

if __name__ == "__main__":
    confirm = input("This will erase all data in your database. Continue? (y/N): ")
    if confirm.lower() == "y":
        clear_db()
    else:
        print("Database clear cancelled.")