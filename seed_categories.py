# app/db/seed_categories.py
import re
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.categories import Category, SubCategory, Brand

# Structured brand records with exact category mapping
BRAND_DATA = [
    # BOTH (Glasses & Sunglasses)
    {"name": "Bottega Veneta", "category_type": "both"},
    {"name": "Bulgari", "category_type": "both"},
    {"name": "Burberry", "category_type": "both"},
    {"name": "Calvin Klein", "category_type": "both"},
    {"name": "Chanel", "category_type": "both"},
    {"name": "Chloe", "category_type": "both"},
    {"name": "D & G", "category_type": "both"},
    {"name": "Diesel", "category_type": "both"},
    {"name": "Dior", "category_type": "both"},
    {"name": "Dolce & Gabbana", "category_type": "both"},
    {"name": "Emporio Armani", "category_type": "both"},
    {"name": "Giorgio Armani", "category_type": "both"},
    {"name": "Gucci", "category_type": "both"},
    {"name": "Hugo Boss", "category_type": "both"},
    {"name": "Jimmy Choo", "category_type": "both"},
    {"name": "Joules", "category_type": "both"},
    {"name": "Lacoste", "category_type": "both"},
    {"name": "Marc Jacobs", "category_type": "both"},
    {"name": "McQueen", "category_type": "both"},
    {"name": "Michael Kors", "category_type": "both"},
    {"name": "Moschino", "category_type": "both"},
    {"name": "Nike", "category_type": "both"},
    {"name": "Oakley", "category_type": "both"},
    {"name": "Persol", "category_type": "both"},
    {"name": "Polo Ralph Lauren", "category_type": "both"},
    {"name": "Prada", "category_type": "both"},
    {"name": "Prada Linea Rossa", "category_type": "both"},
    {"name": "Radley", "category_type": "both"},
    {"name": "Ralph Lauren", "category_type": "both"},
    {"name": "Ray-Ban", "category_type": "both"},
    {"name": "Ray-Ban Junior", "category_type": "both"},
    {"name": "Red Bull", "category_type": "both"},
    {"name": "Saint Laurent", "category_type": "both"},
    {"name": "Superdry", "category_type": "both"},
    {"name": "Tag Heuer", "category_type": "both"},
    {"name": "Ted Baker", "category_type": "both"},
    {"name": "Tiffany", "category_type": "both"},
    {"name": "Tom Ford", "category_type": "both"},
    {"name": "Valentino", "category_type": "both"},
    {"name": "Versace", "category_type": "both"},
    {"name": "Vogue", "category_type": "both"},
    {"name": "Yves Saint Laurent", "category_type": "both"},

    # GLASSES ONLY
    {"name": "Adidas", "category_type": "glasses"},
    {"name": "Alain Mikli", "category_type": "glasses"},
    {"name": "Arsenal FC", "category_type": "glasses"},
    {"name": "Bench", "category_type": "glasses"},
    {"name": "Bobbi Brown", "category_type": "glasses"},
    {"name": "Chelsea FC", "category_type": "glasses"},
    {"name": "Converse", "category_type": "glasses"},
    {"name": "Crosshatch", "category_type": "glasses"},
    {"name": "DKNY", "category_type": "glasses"},
    {"name": "Etnia Barcelona", "category_type": "glasses"},
    {"name": "Everton FC", "category_type": "glasses"},
    {"name": "Fendi", "category_type": "glasses"},
    {"name": "Hugo Boss Orange", "category_type": "glasses"},
    {"name": "Kate Spade", "category_type": "glasses"},
    {"name": "Liverpool FC", "category_type": "glasses"},
    {"name": "Manchester City FC", "category_type": "glasses"},
    {"name": "Manchester United FC", "category_type": "glasses"},
    {"name": "Marc by Marc Jacobs", "category_type": "glasses"},
    {"name": "Max Mara", "category_type": "glasses"},
    {"name": "Montblanc", "category_type": "glasses"},
    {"name": "Oasis", "category_type": "glasses"},
    {"name": "Salvatore Ferragamo", "category_type": "glasses"},
    {"name": "Silhouette", "category_type": "glasses"},
    {"name": "Smith Optics", "category_type": "glasses"},
    {"name": "Starck Eyes", "category_type": "glasses"},
    {"name": "Stella McCartney", "category_type": "glasses"},
    {"name": "Swarovski", "category_type": "glasses"},

    # SUNGLASSES ONLY
    {"name": "Alexander McQueen", "category_type": "sunglasses"},
    {"name": "Barbour", "category_type": "sunglasses"},
    {"name": "Carrera", "category_type": "sunglasses"},
    {"name": "DSL 55", "category_type": "sunglasses"},
    {"name": "Nautica", "category_type": "sunglasses"},
]

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
        # Clear existing entries if necessary or handle fresh database seed
        if db.query(Category).first():
            print("Database already seeded. Clear table records to re-seed fresh brands.")
            return

        print("Seeding Main Categories...")
        cat_glasses = Category(name="Glasses", slug="glasses", is_main_nav=True, display_order=1)
        cat_sunglasses = Category(name="Sunglasses", slug="sunglasses", is_main_nav=True, display_order=2)
        cat_lenses = Category(name="Lenses", slug="lenses", is_main_nav=True, display_order=3)
        cat_notice = Category(name="To Notice", slug="to-notice", is_main_nav=True, display_order=4)
        cat_contacts = Category(name="Contact Lenses", slug="contact-lenses", is_main_nav=True, display_order=5)
        cat_sale = Category(name="Sale", slug="sale", is_main_nav=True, display_order=6)

        db.add_all([cat_glasses, cat_sunglasses, cat_lenses, cat_notice, cat_contacts, cat_sale])
        db.commit()

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

        print(f"Seeding {len(BRAND_DATA)} Categorized Brands...")
        brands_dict = {}
        for brand_info in BRAND_DATA:
            b_name = brand_info["name"]
            b_slug = slugify(b_name)
            is_pop = b_name in POPULAR_BRANDS
            
            brand_obj = Brand(
                name=b_name, 
                slug=b_slug, 
                is_popular=is_pop,
                category_type=brand_info["category_type"]
            )
            db.add(brand_obj)
            brands_dict[b_name] = brand_obj

        db.commit()

        print("Linking Brands to Subcategories...")
        for brand_name, brand_obj in brands_dict.items():
            if brand_obj.is_popular:
                subcategories_dict["Best Sellers"].brands.append(brand_obj)
                subcategories_dict["New Arrivals"].brands.append(brand_obj)

            if "Ray-Ban" in brand_name:
                subcategories_dict["Ray-Ban Meta"].brands.append(brand_obj)
            elif "Oakley" in brand_name:
                subcategories_dict["Oakley Meta"].brands.append(brand_obj)

            subcategories_dict["Women's Glasses"].brands.append(brand_obj)
            subcategories_dict["Men's Glasses"].brands.append(brand_obj)

        db.commit()
        print("Successfully seeded all categories, subcategories, and categorized brands!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()