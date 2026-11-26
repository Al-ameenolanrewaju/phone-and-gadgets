"""One-time starter catalogue for the Phone & Gadgets store.

Images are externally hosted illustrative product photos. Replace with exact
stock photos before representing a listing as a specific model or stock item.
"""
from decimal import Decimal

from . import db
from .models import Business, Category, Product, ProductImage, ProductVariant
from .utils import slugify

# Product-specific cover images. Each listing gets its own image rather than
# sharing one category-wide image across unrelated products.
PRODUCT_IMAGES = {
    "Apple iPhone 13 128GB": [
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-13-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-13-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-13-3.jpg",
    ],
    "Apple iPhone 11 64GB": [
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-11-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-11-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-11-3.jpg",
    ],
    "Samsung Galaxy A15 128GB": [
        "https://plazait.co.id/uploads/products/gallery/ginee_20240821170545772_9619520084.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-a15-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-a15-2.jpg",
    ],
    "Samsung Galaxy A05s 128GB": [
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-a05s-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-a05s-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-a05s-3.jpg",
    ],
    "Samsung Galaxy S23 256GB": [
        "https://cdn-files.kimovil.com/default/0008/33/thumb_732931_default_big.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-s23-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-s23-2.jpg",
    ],
    "Tecno Spark 20 256GB": [
        "https://sota.store/image/cache/catalog/Tecno/tecno-Spark-20-KJ5n-gld-02-1600x1600.webp",
        "https://sota.store/image/cache/catalog/Tecno/tecno-Spark-20-KJ5n-gld-03-1600x1600.webp",
        "https://fdn2.gsmarena.com/vv/pics/tecno/tecno-spark-20-1.jpg",
    ],
    "Tecno Camon 20 256GB": [
        "https://fdn2.gsmarena.com/vv/pics/tecno/tecno-camon-20-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/tecno/tecno-camon-20-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/tecno/tecno-camon-20-3.jpg",
    ],
    "Infinix Hot 40i 128GB": [
        "https://fdn2.gsmarena.com/vv/pics/infinix/infinix-hot-40i-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/infinix/infinix-hot-40i-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/infinix/infinix-hot-40i-3.jpg",
    ],
    "Infinix Note 30 256GB": [
        "https://cdn.hoanghamobile.vn/Uploads/2023/08/21/infinix-note-30-4.png",
        "https://fdn2.gsmarena.com/vv/pics/infinix/infinix-note-30-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/infinix/infinix-note-30-2.jpg",
    ],
    "Redmi 13C 128GB": [
        "https://fdn2.gsmarena.com/vv/pics/xiaomi/xiaomi-redmi-13c-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/xiaomi/xiaomi-redmi-13c-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/xiaomi/xiaomi-redmi-13c-3.jpg",
    ],
    "HP Core i5 Laptop 8GB RAM": [
        "https://media.loveitopcdn.com/25799/thumb/10933-hp-elitebook-830-g8-3.jpg",
        "https://www.hp.com/content/dam/sites/worldwide/personal-computers/consumer/laptops-and-2-in-1s/elitebook-830-g8/elitebook-830-g8-hero.png",
        "https://www.notebookcheck.net/fileadmin/Notebooks/HP/EliteBook_830_G8/4zu3_HP_EliteBook_830_G8.jpg",
    ],
    "Lenovo ThinkPad Core i5": [
        "https://www.notebookcheck.net/fileadmin/Notebooks/Lenovo/ThinkPad_T480/4zu3_T480.jpg",
        "https://www.notebookcheck.net/fileadmin/Notebooks/Lenovo/ThinkPad_T480/4zu3_T480_2.jpg",
        "https://www.notebookcheck.net/fileadmin/Notebooks/Lenovo/ThinkPad_T480/4zu3_T480_3.jpg",
    ],
    "Samsung Galaxy Tab A8": [
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-tab-a8-10-5-1.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-tab-a8-10-5-2.jpg",
        "https://fdn2.gsmarena.com/vv/pics/samsung/samsung-galaxy-tab-a8-10-5-3.jpg",
    ],
    "Oraimo 20000mAh Power Bank": [
        "https://djokstore.ci/cdn/shop/files/1_50471d38-dc64-4268-88ce-49609bf1e8ed.jpg?v=1699532264",
        "https://djokstore.ci/cdn/shop/files/2_50471d38-dc64-4268-88ce-49609bf1e8ed.jpg?v=1699532264",
        "https://djokstore.ci/cdn/shop/files/3_50471d38-dc64-4268-88ce-49609bf1e8ed.jpg?v=1699532264",
    ],
    "Oraimo FreePods 3 Earbuds": [
        "https://tunzaa.nyc3.digitaloceanspaces.com/products/cover_images/825_0_1757433879.jpg",
        "https://tunzaa.nyc3.digitaloceanspaces.com/products/gallery_images/825_1_1757433879.jpg",
        "https://tunzaa.nyc3.digitaloceanspaces.com/products/gallery_images/825_2_1757433879.jpg",
    ],
    "Oraimo BoomPop 2 Headphones": [
        "https://www.oraimo.com/cdn/shop/files/boompop2-black.png",
        "https://www.oraimo.com/cdn/shop/files/boompop2-black-side.png",
        "https://www.oraimo.com/cdn/shop/files/boompop2-black-detail.png",
    ],
    "Oraimo SoundGo 2 Bluetooth Speaker": [
        "https://www.oraimo.com/cdn/shop/files/soundgo2-black.png",
        "https://www.oraimo.com/cdn/shop/files/soundgo2-black-side.png",
        "https://www.oraimo.com/cdn/shop/files/soundgo2-black-detail.png",
    ],
    "Oraimo Watch 4 Plus Smartwatch": [
        "https://www.oraimo.com/cdn/shop/files/watch4plus-black.png",
        "https://www.oraimo.com/cdn/shop/files/watch4plus-black-side.png",
        "https://www.oraimo.com/cdn/shop/files/watch4plus-black-detail.png",
    ],
    "20W USB-C Fast Charger": [
        "https://www.oraimo.com/cdn/shop/files/charger-20w.png",
        "https://www.oraimo.com/cdn/shop/files/charger-20w-side.png",
        "https://www.oraimo.com/cdn/shop/files/charger-20w-detail.png",
    ],
    "USB-C Fast Charging Cable": [
        "https://www.oraimo.com/cdn/shop/files/usb-c-cable.png",
        "https://www.oraimo.com/cdn/shop/files/usb-c-cable-detail.png",
        "https://www.oraimo.com/cdn/shop/files/usb-c-cable-package.png",
    ],
}

PRODUCTS = [
    ("Apple iPhone 13 128GB", 485000, "iPhone", "128GB", "Midnight"),
    ("Apple iPhone 11 64GB", 285000, "iPhone", "64GB", "Black"),
    ("Samsung Galaxy A15 128GB", 235000, "Samsung", "128GB", "Blue Black"),
    ("Samsung Galaxy A05s 128GB", 185000, "Samsung", "128GB", "Black"),
    ("Samsung Galaxy S23 256GB", 650000, "Samsung", "256GB", "Cream"),
    ("Tecno Spark 20 256GB", 195000, "Android Phones", "256GB", "Gravity Black"),
    ("Tecno Camon 20 256GB", 245000, "Android Phones", "256GB", "Serenity Blue"),
    ("Infinix Hot 40i 128GB", 175000, "Android Phones", "128GB", "Palm Blue"),
    ("Infinix Note 30 256GB", 255000, "Android Phones", "256GB", "Obsidian Black"),
    ("Redmi 13C 128GB", 165000, "Android Phones", "128GB", "Midnight Black"),
    ("HP Core i5 Laptop 8GB RAM", 650000, "Laptops", "256GB SSD", "Silver"),
    ("Lenovo ThinkPad Core i5", 580000, "Laptops", "256GB SSD", "Black"),
    ("Samsung Galaxy Tab A8", 320000, "Tablets", "64GB", "Grey"),
    ("Oraimo 20000mAh Power Bank", 42000, "Power Banks", "20000mAh", "Black"),
    ("Oraimo FreePods 3 Earbuds", 38000, "Earbuds", "Bluetooth", "White"),
    ("Oraimo BoomPop 2 Headphones", 32000, "Headphones", "Bluetooth", "Black"),
    ("Oraimo SoundGo 2 Bluetooth Speaker", 28000, "Speakers", "Portable", "Black"),
    ("Oraimo Watch 4 Plus Smartwatch", 55000, "Smartwatches", "Smart watch", "Black"),
    ("20W USB-C Fast Charger", 18000, "Chargers", "20W", "White"),
    ("USB-C Fast Charging Cable", 6500, "Cables", "1 metre", "White"),
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
            for index, (name, price, category_name, storage, colour) in enumerate(PRODUCTS, 1):
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

def register_product_image_refresh_command(app):
    @app.cli.command("refresh-phone-gadgets-product-images")
    def refresh_phone_gadgets_product_images():
        """Replace duplicated category photos with product-specific cover images."""
        business = Business.query.filter_by(slug="phone-gadgets", status="ACTIVE").first()
        if not business:
            raise RuntimeError("Phone & Gadgets store not found.")
        updated = 0
        try:
            for product_name, urls in PRODUCT_IMAGES.items():
                product = Product.query.filter_by(business_id=business.id, name=product_name).first()
                if not product:
                    continue
                for image in list(product.images):
                    db.session.delete(image)
                db.session.flush()
                for position, url in enumerate(urls, 1):
                    db.session.add(ProductImage(
                        business_id=business.id,
                        product_id=product.id,
                        url=url,
                        alt_text=f"{product.name} product photo",
                        sort_order=position - 1,
                        original_filename=f"product-{product.slug}-{position}.jpg",
                    ))
                updated += 1
            db.session.commit()
            print(f"Updated product-specific photos for {updated} products.")
        except Exception:
            db.session.rollback()
            raise
