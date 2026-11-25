from decimal import Decimal

from . import db
from .models import Category, Product, ProductImage, ProductVariant, StoreSettings


SAMPLE_PRODUCTS = [
    ("iPhone 15 Pro", "demo-iphone-15-pro", "iPhone", "1450000", "iOS", "New", "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=1000&q=85", [("128GB", "Natural Titanium", 3), ("256GB", "Black Titanium", 2)]),
    ("Samsung Galaxy S24 Ultra", "demo-samsung-galaxy-s24-ultra", "Samsung", "1780000", "Android", "New", "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=1000&q=85", [("256GB", "Titanium Gray", 3), ("512GB", "Titanium Black", 2)]),
    ("Google Pixel 8 Pro", "demo-google-pixel-8-pro", "Android Phones", "980000", "Android", "New", "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1000&q=85", [("128GB", "Obsidian", 2), ("256GB", "Bay", 2)]),
    ("MacBook Air 13-inch", "demo-macbook-air-13", "Laptops", "1650000", "macOS", "New", "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=1000&q=85", [("256GB SSD", "Midnight", 2), ("512GB SSD", "Silver", 2)]),
    ("HP EliteBook 840", "demo-hp-elitebook-840", "Laptops", "890000", "Windows", "Refurbished", "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1000&q=85", [("512GB SSD", "Silver", 3)]),
    ("Apple AirPods Pro", "demo-airpods-pro", "Earbuds", "285000", "iOS", "New", "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=1000&q=85", [("Standard", "White", 5)]),
    ("Anker Power Bank", "demo-anker-power-bank", "Power Banks", "125000", "Universal", "New", "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?auto=format&fit=crop&w=1000&q=85", [("20000mAh", "Black", 6)]),
    ("Apple Watch Series", "demo-apple-watch-series", "Smartwatches", "420000", "iOS", "New", "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?auto=format&fit=crop&w=1000&q=85", [("41mm", "Midnight", 2), ("45mm", "Starlight", 2)]),
    ("Sony Wireless Headphones", "demo-sony-wireless-headphones", "Headphones", "310000", "Universal", "New", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1000&q=85", [("Standard", "Black", 3)]),
    ("PlayStation 5 Slim", "demo-playstation-5-slim", "Gaming", "980000", "Universal", "New", "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=1000&q=85", [("1TB", "White", 2)]),
]


def seed_demo_catalogue_data(business):
    categories = {
        category.name.casefold(): category
        for category in Category.query.filter_by(business_id=business.id).all()
    }
    added = 0
    for index, (name, slug, category_name, price, compatibility, condition, image_url, variants) in enumerate(SAMPLE_PRODUCTS):
        category = categories.get(category_name.casefold())
        if category is None:
            raise RuntimeError(f"Required demo category is missing: {category_name}")
        product = Product.query.filter_by(business_id=business.id, slug=slug).first()
        if product is not None:
            continue
        product = Product(
            business_id=business.id,
            category_id=category.id,
            name=f"{name} (Demo)",
            slug=slug,
            description=f"{name}: sample catalogue listing for preview only. Product details, price and stock are illustrative, not a live offer.",
            regular_price=Decimal(price),
            gender=compatibility,
            electronics_type=condition,
            featured=index < 4,
            new_arrival=True,
            is_published=True,
            sku="DEMO-" + slug.upper().replace("-", "")[-12:],
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(ProductImage(
            business_id=business.id,
            product_id=product.id,
            url=image_url,
            alt_text=f"{name} demo product image",
            sort_order=0,
        ))
        for storage, colour, stock in variants:
            db.session.add(ProductVariant(
                business_id=business.id,
                product_id=product.id,
                storage=storage,
                colour=colour,
                stock_quantity=stock,
                is_available=True,
            ))
        added += 1

    settings = StoreSettings.query.filter_by(business_id=business.id).first()
    if settings:
        settings.announcement = "Preview catalogue — sample products and prices"
        settings.hero_title = "Explore phones, gadgets and everyday technology."
        settings.catalogue_title = "Explore the demo catalogue"
        settings.about_text = "This preview store contains sample products. Product names, prices and stock are illustrative only."
    db.session.commit()
    return added


def register_demo_catalogue_command(app):
    @app.cli.command("seed-demo-catalogue")
    def seed_demo_catalogue():
        """Add clearly identified demo products to the preview store, safely and idempotently."""
        from .models import Business

        business = Business.query.filter_by(slug="phone-gadgets", status="ACTIVE").first()
        if business is None:
            raise RuntimeError("Phone & Gadgets store must be bootstrapped before adding demo products.")
        added = seed_demo_catalogue_data(business)
        print(f"Demo catalogue ready: {len(SAMPLE_PRODUCTS)} sample products; {added} newly added.")
