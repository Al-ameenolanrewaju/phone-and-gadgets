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

# Product-specific cover images. Each listing gets its own image rather than
# sharing one category-wide image across unrelated products.
PRODUCT_IMAGES = {
    "Apple iPhone 13 128GB": ["https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-13-01.jpg"],
    "Apple iPhone 11 64GB": ["https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-11-1.jpg"],
    "Samsung Galaxy A15 128GB": ["https://plazait.co.id/uploads/products/gallery/ginee_20240821170545772_9619520084.jpg"],
    "Samsung Galaxy A05s 128GB": ["https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-a05s-1.jpg"],
    "Samsung Galaxy S23 256GB": ["https://cdn-files.kimovil.com/default/0008/33/thumb_732931_default_big.jpg"],
    "Tecno Spark 20 256GB": ["https://sota.store/image/cache/catalog/Tecno/tecno-Spark-20-KJ5n-gld-02-1600x1600.webp"],
    "Tecno Camon 20 256GB": ["https://fdn2.gsmarena.com/vv/pics/tecno/tecno-camon-20-1.jpg"],
    "Infinix Hot 40i 128GB": ["https://fdn2.gsmarena.com/vv/pics/infinix/infinix-hot-40i-1.jpg"],
    "Infinix Note 30 256GB": ["https://cdn.hoanghamobile.vn/Uploads/2023/08/21/infinix-note-30-4.png"],
    "Redmi 13C 128GB": ["https://www.mi.com/ng/product/redmi-13c/"],
    "HP Core i5 Laptop 8GB RAM": ["https://media.loveitopcdn.com/25799/thumb/10933-hp-elitebook-830-g8-3.jpg"],
    "Lenovo ThinkPad Core i5": ["https://www.notebookcheck.net/fileadmin/Notebooks/Lenovo/ThinkPad_T480/4zu3_T480.jpg"],
    "Samsung Galaxy Tab A8": ["https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-tab-a8-10-5-1.jpg"],
    "Oraimo 20000mAh Power Bank": ["https://djokstore.ci/cdn/shop/files/1_50471d38-dc64-4268-88ce-49609bf1e8ed.jpg?v=1699532264"],
    "Oraimo FreePods 3 Earbuds": ["https://tunzaa.nyc3.digitaloceanspaces.com/products/cover_images/825_0_1757433879.jpg"],
    "Oraimo BoomPop 2 Headphones": ["https://www.oraimo.com/cdn/shop/files/boompop2-black.png"],
    "Oraimo SoundGo 2 Bluetooth Speaker": ["https://www.oraimo.com/cdn/shop/files/soundgo2-black.png"],
    "Oraimo Watch 4 Plus Smartwatch": ["https://www.oraimo.com/cdn/shop/files/watch4plus-black.png"],
    "20W USB-C Fast Charger": ["https://www.oraimo.com/cdn/shop/files/charger-20w.png"],
    "USB-C Fast Charging Cable": ["https://www.oraimo.com/cdn/shop/files/usb-c-cable.png"],
}

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
        """Add 20 sample products with product-specific cover photos, once."""
        business = Business.query.filter_by(slug="phone-gadgets", status="ACTIVE").first()
        if not business:
            raise RuntimeError("The Phone & Gadgets store has not been bootstrapped.")
        existing = Product.query.filter_by(business_id=business.id).count()
        if existing >= len(PRODUCTS):
            print(f"Catalogue already contains {existing} products; seed is complete.")
            return
        if existing:
            raise RuntimeError(
                f"Catalogue contains {existing} products; refusing a partial/duplicate import."
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
                for position, url in enumerate(PRODUCT_IMAGES[name], 1):
                    db.session.add(ProductImage(
                        business_id=business.id,
                        product_id=product.id,
                        url=url,
                        alt_text=f"{name} - gallery photo {position}",
                        sort_order=position - 1,
                        original_filename=f"sample-{index:02d}-{position:02d}.jpg",
                    ))
            db.session.commit()
            print("Added 20 sample products with product-specific cover photos.")
        except Exception:
            db.session.rollback()
            raise
