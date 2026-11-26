"""One-time starter catalogue for the Phone & Gadgets store.

Images are externally hosted illustrative product photos. Replace with exact
stock photos before representing a listing as a specific model or stock item.
"""
from decimal import Decimal
from flask import current_app
from sqlalchemy import func

from . import db
from .models import Business, Category, Product, ProductImage, ProductVariant
from .utils import slugify

# Three illustrative gallery photos per listing. These are public product/editorial
# image URLs; they are not guaranteed to depict the exact model in each title.
PHONE_IMAGES = [
    "https://images.unsplash.com/photo-1729514552998-cdb2975826cf?auto=format&fit=crop&w=1200&q=85",
    "https://images-bonnier.imgix.net/files/kom/production/2024/10/17130840/android-vs-iphone.jpg?auto=format&fit=crop&w=1200&q=85",
    "https://images.unsplash.com/photo-1729514552998-cdb2975826cf?auto=format&fit=crop&w=1200&q=85&sat=-15",
]
GADGET_IMAGES = [
    "https://cdn.shopify.com/s/files/1/0689/2932/3085/collections/a-bunch-of-electronics.png?v=1769371963",
    "https://gizzmo.si/artikli-slike/94385/teen-tech-kit-komplet-za-glasbo-in-urejeno-mizo-src-uncropped.jpg",
    "https://doctorhead.ru/upload/dev2fun.imagecompress/webp/iblock/f89/p1co9ffl6gx30b06ojtkpg01gbydk6sr/IMG_4448.webp",
]

PRODUCTS = [
    ("Apple iPhone 13 128GB", 485000, "iPhone", "128GB", "Midnight", PHONE_IMAGES),
    ("Apple iPhone 11 64GB", 285000, "iPhone", "64GB", "Black", PHONE_IMAGES),
    ("Samsung Galaxy A15 128GB", 235000, "Samsung", "128GB", "Blue Black", PHONE_IMAGES),
    ("Samsung Galaxy A05s 128GB", 185000, "Samsung", "128GB", "Black", PHONE_IMAGES),
    ("Samsung Galaxy S23 256GB", 650000, "Samsung", "256GB", "Cream", PHONE_IMAGES),
    ("Tecno Spark 20 256GB", 195000, "Android Phones", "256GB", "Gravity Black", PHONE_IMAGES),
    ("Tecno Camon 20 256GB", 245000, "Android Phones", "256GB", "Serenity Blue", PHONE_IMAGES),
    ("Infinix Hot 40i 128GB", 175000, "Android Phones", "128GB", "Palm Blue", PHONE_IMAGES),
    ("Infinix Note 30 256GB", 255000, "Android Phones", "256GB", "Obsidian Black", PHONE_IMAGES),
    ("Redmi 13C 128GB", 165000, "Android Phones", "128GB", "Midnight Black", PHONE_IMAGES),
    ("HP Core i5 Laptop 8GB RAM", 650000, "Laptops", "256GB SSD", "Silver", GADGET_IMAGES),
    ("Lenovo ThinkPad Core i5", 580000, "Laptops", "256GB SSD", "Black", GADGET_IMAGES),
    ("Samsung Galaxy Tab A8", 320000, "Tablets", "64GB", "Grey", GADGET_IMAGES),
    ("Oraimo 20000mAh Power Bank", 42000, "Power Banks", "20000mAh", "Black", GADGET_IMAGES),
    ("Oraimo FreePods 3 Earbuds", 38000, "Earbuds", "Bluetooth", "White", GADGET_IMAGES),
    ("Oraimo BoomPop 2 Headphones", 32000, "Headphones", "Bluetooth", "Black", GADGET_IMAGES),
    ("Oraimo SoundGo 2 Bluetooth Speaker", 28000, "Speakers", "Portable", "Black", GADGET_IMAGES),
    ("Oraimo Watch 4 Plus Smartwatch", 55000, "Smartwatches", "Smart watch", "Black", GADGET_IMAGES),
    ("20W USB-C Fast Charger", 18000, "Chargers", "20W", "White", GADGET_IMAGES),
    ("USB-C Fast Charging Cable", 6500, "Cables", "1 metre", "White", GADGET_IMAGES),
]


def register_sample_catalogue_command(app):
    @app.cli.command("seed-phone-gadgets-catalogue")
    def seed_phone_gadgets_catalogue():
        """Add 20 sample products, each with a three-photo gallery, once."""
        business = Business.query.filter_by(slug="phone-gadgets", status="ACTIVE").first()
        if not business:
            raise RuntimeError("The Phone & Gadgets store has not been bootstrapped.")
        existing = Product.query.filter_by(business_id=business.id).count()
        if existing:
            raise RuntimeError(
                f"Catalogue already contains {existing} products; refusing to add duplicates."
            )
        categories = {
            c.name.lower(): c
            for c in Category.query.filter_by(business_id=business.id).all()
        }
        db.session.execute(db.text("SET LOCAL search_path TO gadgets"))
        try:
            for index, (name, price, category_name, storage, colour, images) in enumerate(PRODUCTS, 1):
                category = categories.get(category_name.lower())
                if not category:
                    raise RuntimeError(f"Missing store category: {category_name}")
                product = Product(
                    business_id=business.id,
                    category_id=category.id,
                    name=name,
                    slug=slugify(name),
                    description=(
                        f"{name}. Sample catalogue listing for the Nigerian market. "
                        "Confirm exact model specifications, condition, availability and price before purchase."
                    ),
                    regular_price=Decimal(str(price)),
                    gender="Universal",
                    electronics_type="New",
                    featured=index <= 4,
                    new_arrival=True,
                    is_published=True,
                    sku=f"PG-SAMPLE-{index:03d}",
                )
                db.session.add(product)
                db.session.flush()
                db.session.add(ProductVariant(
                    business_id=business.id,
                    product_id=product.id,
                    storage=storage,
                    colour=colour,
                    stock_quantity=0,
                    is_available=False,
                ))
                for position, url in enumerate(images, 1):
                    db.session.add(ProductImage(
                        business_id=business.id,
                        product_id=product.id,
                        url=url,
                        alt_text=f"{name} - gallery photo {position}",
                        sort_order=position - 1,
                        original_filename=f"sample-{index:02d}-{position:02d}.jpg",
                    ))
            db.session.commit()
            print("Added 20 sample products with 3 gallery photos each (60 image entries).")
        except Exception:
            db.session.rollback()
            raise
