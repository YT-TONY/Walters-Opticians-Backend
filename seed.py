from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.product import Product
from app.core.security import get_password_hash


def seed_db():
    # 1. Ensure all database tables exist before querying
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # 2. Check if Admin exists with BOTH id=0 AND the admin email
        admin = db.query(User).filter(
            User.id == 0,
            User.email == "admin@walters-opticians.com"
        ).first()

        if not admin:
            admin = User(
                id=0,  # Explicitly assign ID 0 to Admin
                full_name="Walters Admin",
                email="admin@walters-opticians.com",
                hashed_password=get_password_hash("AdminSecret123!"),
                role=UserRole.ADMIN
            )
            db.add(admin)
            db.commit()

            # Safely set the auto-increment sequence in SQLite so the first customer gets ID 1
            if "sqlite" in str(engine.url):
                try:
                    db.execute(text("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'users';"))
                    db.commit()
                except OperationalError:
                    # sqlite_sequence doesn't exist yet; insert the initial sequence row manually
                    try:
                        db.execute(text("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', 0);"))
                        db.commit()
                    except OperationalError:
                        pass  # If sqlite_sequence isn't used yet, SQLite will default the next id to 1 automatically

            print("✓ Admin account created with ID = 0.")
        else:
            print("✓ Admin account (ID: 0) already exists.")

        # 3. Seed Sample Frame Catalog
        sample_products = [
            {
                "name": "Avery",
                "brand": "Valorée Eyewear",
                "shape": "Round",
                "color_description": "Tortoise Amber",
                "price_full_gbp": 168.0,
                "allow_frame_only": True,
                "price_frame_only_gbp": 128.0,
                "image_url": "https://images.unsplash.com/photo-1572635196237-14b3f281503f?auto=format&fit=crop&q=80&w=600",
                "is_featured": True
            },
            {
                "name": "Marlowe",
                "brand": "Valorée Eyewear",
                "shape": "Rectangle",
                "color_description": "Cobalt Depth",
                "price_full_gbp": 185.0,
                "allow_frame_only": True,
                "price_frame_only_gbp": 145.0,
                "image_url": "https://images.unsplash.com/photo-1591076482161-42ce6da69f67?auto=format&fit=crop&q=80&w=600",
                "is_featured": True
            },
            {
                "name": "Sable",
                "brand": "Tom Ford",
                "shape": "Aviator",
                "color_description": "Polished Gold",
                "price_full_gbp": 205.0,
                "allow_frame_only": True,
                "price_frame_only_gbp": 165.0,
                "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&q=80&w=600",
                "is_featured": False
            },
            {
                "name": "Lumen",
                "brand": "Gucci",
                "shape": "Square",
                "color_description": "Signal Yellow",
                "price_full_gbp": 176.0,
                "allow_frame_only": True,
                "price_frame_only_gbp": 136.0,
                "image_url": "https://images.unsplash.com/photo-1577803645773-f96470509666?auto=format&fit=crop&q=80&w=600",
                "is_featured": True
            }
        ]

        products_added = 0
        for p in sample_products:
            if not db.query(Product).filter(Product.name == p["name"]).first():
                db.add(Product(**p))
                products_added += 1

        db.commit()
        print(f"✓ Catalog updated. Added {products_added} new product(s).")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()