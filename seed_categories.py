# app/db/seed_categories.py
import re
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.categories import Category, SubCategory, Brand

# Complete list of unique brands
BRAND_NAMES = [
    "Adidas", "Alain Mikli", "Alexander McQueen", "Arsenal FC", "Barbour", 
    "Bench", "Bobbi Brown", "Bottega Veneta", "Bulgari", "Burberry", 
    "Calvin Klein", "Carrera", "Chanel", "Chelsea FC", "Chloe", 
    "Converse", "Crosshatch", "D & G", "Diesel", "Dior", 
    "DKNY", "Dolce & Gabbana", "DSL 55", "Emporio Armani", "Etnia Barcelona", 
    "Everton FC", "Fendi", "Giorgio Armani", "Gucci", "Hugo Boss", 
    "Hugo Boss Orange", "Jimmy Choo", "Joules", "Kate Spade", "Lacoste", 
    "Liverpool FC", "Manchester City FC", "Manchester United FC", "Marc by Marc Jacobs", 
    "Marc Jacobs", "Max Mara", "McQueen", "Michael Kors", "Montblanc", 
    "Moschino", "Nautica", "Nike", "Oakley", "Oasis", 
    "Persol", "Polo Ralph Lauren", "Prada", "Prada Linea Rossa", "Radley", 
    "Ralph Lauren", "Ray-Ban", "Ray-Ban Junior", "Red Bull", "Saint Laurent", 
    "Salvatore Ferragamo", "Silhouette", "Smith Optics", "Starck Eyes", "Stella McCartney", 
    "Superdry", "Swarovski", "Tag Heuer", "Ted Baker", "Tiffany", 
    "Tom Ford", "Valentino", "Versace", "Vogue", "Yves Saint Laurent"
]

# Requested Subcategories
SUBCATEGORY_NAMES = [
    "Women's Glasses",
    "Men's Glasses",
    "Kids' Glasses",
    "New Arrivals",
    "Best Sellers",
    "Blue Light Blocking Glasses",
    "Our Favorites",
    "Ray-Ban Meta",
    "Oakley Meta",
    "Sale"
]

POPULAR_BRANDS = {"Ray-Ban", "Gucci", "Tom Ford", "Oakley", "Prada", "Burberry", "Chanel", "Versace"}

def slugify(text: str) -> str:
    text = text.lower().replace("'", "").replace("&", "and")
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '-', text).strip('-')

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Category).first():
            print("Database already contains category data. Skipping seed.")
            return

        print("Seeding Main Categories...")

        # 1. Main Categories
        cat_glasses = Category(name="Glasses", slug="glasses", is_main_nav=True, display_order=1)
        cat_sunglasses = Category(name="Sunglasses", slug="sunglasses", is_main_nav=True, display_order=2)
        cat_lenses = Category(name="Lenses", slug="lenses", is_main_nav=True, display_order=3)
        cat_notice = Category(name="To Notice", slug="to-notice", is_main_nav=True, display_order=4)
        cat_contacts = Category(name="Contact Lenses", slug="contact-lenses", is_main_nav=True, display_order=5)
        cat_sale = Category(name="Sale", slug="sale", is_main_nav=True, display_order=6)

        db.add_all([cat_glasses, cat_sunglasses, cat_lenses, cat_notice, cat_contacts, cat_sale])
        db.commit()

        # 2. Subcategories (under Glasses)
        print("Seeding Subcategories...")
        subcategories_dict = {}
        for sub_name in SUBCATEGORY_NAMES:
            sub_obj = SubCategory(
                category_id=cat_glasses.id,
                name=sub_name,
                slug=slugify(sub_name)
            )
            db.add(sub_obj)
            subcategories_dict[sub_name] = sub_obj

        db.commit()

        # 3. Brands
        print(f"Seeding {len(BRAND_NAMES)} Brands...")
        brands_dict = {}
        for brand_name in BRAND_NAMES:
            b_slug = slugify(brand_name)
            is_pop = brand_name in POPULAR_BRANDS
            brand_obj = Brand(name=brand_name, slug=b_slug, is_popular=is_pop)
            db.add(brand_obj)
            brands_dict[brand_name] = brand_obj

        db.commit()

        # 4. Link Brands to Subcategories dynamically
        print("Linking Brands to Subcategories...")
        for brand_name, brand_obj in brands_dict.items():
            # Link popular brands to Best Sellers & New Arrivals
            if brand_obj.is_popular:
                subcategories_dict["Best Sellers"].brands.append(brand_obj)
                subcategories_dict["New Arrivals"].brands.append(brand_obj)

            # Link specific brand lines
            if "Ray-Ban" in brand_name:
                subcategories_dict["Ray-Ban Meta"].brands.append(brand_obj)
            elif "Oakley" in brand_name:
                subcategories_dict["Oakley Meta"].brands.append(brand_obj)
            
            # General distribution to main subcategories
            subcategories_dict["Women's Glasses"].brands.append(brand_obj)
            subcategories_dict["Men's Glasses"].brands.append(brand_obj)

        db.commit()
        print("Successfully seeded all categories, subcategories, and brands!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()