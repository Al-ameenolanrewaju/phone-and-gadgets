from decimal import Decimal

from . import db


SAMPLE_PRODUCTS = [
    {
        "name": "iPhone 15 Pro",
        "slug": "demo-iphone-15-pro",
        "category": "iPhone",
        "price": "1450000",
        "description": "Demo listing: premium titanium iPhone with an advanced camera system and fast performance.",
        "condition": "New",
        "compatibility": "iOS",
        "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=1000&q=85",
        "variants": [("128GB", "Natural Titanium", 3), ("256GB", "Black Titanium", 2)],
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "slug": "demo-samsung-galaxy-s24-ultra",
        "category": "Samsung",
        "price": "1780000",
        "description": "Demo listing: flagship Android phone with a large display, versatile cameras and S Pen.",
        "condition": "New",
        "compatibility": "Android",
        "image": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=1000&q=85",
        "variants": [("256GB", "Titanium Gray", 3), ("512GB", "Titanium Black", 2)],
    },
    {
        "name": "Google Pixel 8 Pro",
        "slug": "demo-google-pixel-8-pro",
        "category": "Android Phones",
        "price": "980000",
        "description": "Demo listing: clean Android experience with computational photography features.",
        "condition": "New",
        "compatibility": "Android",
        "image": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1000&q=85",
        "variants": [("128GB", "Obsidian", 2), ("256GB", "Bay", 2)],
    },
    {
        "name": "MacBook Air 13-inch",
        "slug": "demo-macbook-air-13",
        "category": "Laptops",
        "price": "1650000",
        "description": "Demo listing: lightweight laptop for work, study and everyday productivity.",
        "condition": "New",
        "compatibility": "macOS",
        "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=1000&q=85",
        "variants": [("256GB SSD", "Midnight", 2), ("512GB SSD", "Silver", 2)],
    },
    {
        "name": "HP EliteBook 840",
        "slug": "demo-hp-elitebook-840",
        "category": "Laptops",
        "price": "890000",
        "description": "Demo listing: business-class laptop for office work, meetings and multitasking.",
        "condition": "Refurbished",
        "compatibility": "Windows",
        "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1000&q=85",
        "variants": [("512GB SSD", "Silver", 3)],
    },
    {
        "name": "Apple AirPods Pro",
        "slug": "demo-airpods-pro",
        "category": "Earbuds",
        "price": "285000",
        "description": "Demo listing: wireless earbuds with active noise cancellation and a compact charging case.",
        "condition": "New",
        "compatibility": "iOS",
        "image": "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=1000&q=85",
        "variants": [("Standard", "White", 5)],
    },
    {
        "name": "Anker Power Bank",
        "slug": "demo-anker-power-bank",
        "category": "Power Banks",
        "price": "125000",
        "description": "Demo listing: high-capacity portable charging for phones and other devices.",
        "condition": "New",
        "compatibility": "Universal",
        "image": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?auto=format&fit=crop&w=1000&q=85",
        "variants": [("20000mAh", "Black", 6)],
    },
    {
        "name": "Apple Watch Series",
        "slug": "demo-apple-watch-series",
        "category": "Smartwatches",
        "price": "420000",
        "description": "Demo listing: everyday smartwatch with activity, notification and fitness features.",
        "condition": "New",
        "compatibility": "iOS",
        "image": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?auto=format&fit=crop&w=1000&q=85",
        "variants": [("41mm", "Midnight", 2), ("45mm", "Starlight", 2)],
    },
    {
        "name": "Sony Wireless Headphones",
        "slug": "demo-sony-wireless-headphones",
        "category": "Headphones",
        "price": "310000",
        "description": "Demo listing: over-ear wireless headphones for music, calls and travel.",
        "condition": "New",
        "compatibility": "Universal",
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1000&q=85",
        "variants": [("Standard", "Black", 3)],
    },
    {
        "name": "PlayStation 5 Slim",
        "slug": "demo-playstation-5-slim",
        "category": "Gaming",
        "price": "980000",
        "description": "Demo listing: current-generation home gaming console for the demo catalogue.",
        "condition": "New",
        "compatibility": "Universal",
        "image": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=1000&q=85",
        "variants": [("1TB", "White", 2)],
    },
]


def register_demo_catalogue_command(app):
    @app.cli.command("seed-demo-catalogue")
    def seed_demo_catalogue():
        """Add clearly identified demo products to the preview store, safely and idempotently."""
        from .models import Business, Category, Product, ProductImage, ProductVariant

        business = Business.query.filter_by(slug="phone-gadgets", status="ACTIVE").first()
        if business is None:
            raise RuntimeError("Phone & Gadgets store must be bootstrapped before adding demo products.")

        categories = {
            category.name.casefold(): category
            for category in Category.query.filter_by(business_id=business.id).all()
        }
        added = 0
        for item in SAMPLE_PRODUCTS:
            category = categories.get(item["category"].casefold())
            if category is None:
                raise RuntimeError(f"Required demo category is missing: {item['category']}")

            product = Product.query.filter_by(
                business_id=business.id, slug=item["slug"]
            ).first()
            if product is None:
                product = Product(
                    business_id=business.id,
                    category_id=category.id,
                    name=item["name"] + " (Demo)",
                    slug=item["slug"],
                    description=item["description"] + " Sample catalogue item for preview only; not a live offer.",
                    regular_price=Decimal(item["price"]),
                    gender=item["compatibility"],
                    electronics_type=item["condition"],
                    featured=added < 4,
                    new_arrival=True,
                    is_published=True,
                    sku="DEMO-" + item["slug"].upper().replace("-", "")[-12:],
                )
                db.session.add(product)
                db.session.flush()
                db.session.add(ProductImage(
                    business_id=business.id,
                    product_id=product.id,
                    url=item["image"],
                    alt_text=item["name"] + " demo product image",
                    sort_order=0,
                ))
                for storage, colour, stock in item["variants"]:
                    db.session.add(ProductVariant(
                        business_id=business.id,
                        product_id=product.id,
                        storage=storage,
                        colour=colour,
                        stock_quantity=stock,
                        is_available=True,
                    ))
                added += 1

        settings = db.session.query(__import__("app.models", fromlist=["StoreSettings"]).StoreSettings).filter_by(business_id=business.id).first()
        if settings:
            settings.announcement = "Preview catalogue — sample products and prices"
            settings.hero_title = "Explore phones, gadgets and everyday technology."
            settings.catalogue_title = "Explore the demo catalogue"
            settings.about_text = "This is a preview store populated with sample products. Product names, prices and stock are illustrative only."
        db.session.commit()
        print(f"Demo catalogue ready: {len(SAMPLE_PRODUCTS)} sample products; {added} newly added.")
