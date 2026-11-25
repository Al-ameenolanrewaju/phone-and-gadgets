import re
from io import BytesIO
from urllib.parse import unquote

import pytest
from werkzeug.datastructures import FileStorage

from app import create_app, db
from app.models import (
    ActivityLog,
    Business,
    Category,
    Customer,
    Domain,
    Order,
    OrderItem,
    PasswordResetToken,
    Product,
    ProductImage,
    ProductVariant,
    StoreEvent,
    StoreSettings,
    User,
)
from app.media import delete_image, upload_image, validate_image
from app.utils import normalize_domain


class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret"
    SESSION_COOKIE_SECURE = False
    DEFAULT_STORE_SLUG = None


class CsrfConfig(TestConfig):
    WTF_CSRF_ENABLED = True


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_tenant(app, name="Store A", slug="store-a", host="store-a.test"):
    with app.app_context():
        business = Business(
            name=name,
            slug=slug,
            status="ACTIVE",
            whatsapp_number="2348000000000",
            brand_color="#242424",
        )
        db.session.add(business)
        db.session.flush()
        db.session.add(Domain(
            business_id=business.id,
            host=host,
            status="CONNECTED",
            provider_status="VERIFIED",
            is_primary=True,
        ))
        owner = User(business_id=business.id, name="Owner", email=f"{slug}@example.com", role="OWNER")
        owner.set_password("secret123")
        db.session.add(owner)
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(name="Admin", email="admin@example.com", role="SUPER_ADMIN")
            admin.set_password("secret123")
            db.session.add(admin)
        db.session.commit()
        return business.id, owner.id


def make_product(app, business_id, **values):
    defaults = {
        "business_id": business_id,
        "name": "Linen Shirt",
        "slug": "linen-shirt",
        "description": "A relaxed linen shirt",
        "regular_price": 25000,
        "gender": "Men",
        "electronics_type": "Ready-to-wear",
        "is_published": True,
    }
    defaults.update(values)
    with app.app_context():
        product = Product(**defaults)
        db.session.add(product)
        db.session.commit()
        return product.id


def login_owner(client, slug="store-a", host="store-a.test"):
    return client.post(
        "/login",
        data={"email": f"{slug}@example.com", "password": "secret123"},
        base_url=f"http://{host}",
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_missing_secret_key_prevents_non_test_startup(monkeypatch):
    class ProductionConfig:
        TESTING = False
        SECRET_KEY = None

    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(ProductionConfig)


def test_short_secret_key_prevents_non_test_startup(monkeypatch):
    class ProductionConfig:
        TESTING = False
        SECRET_KEY = "too-short"

    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="32 characters"):
        create_app(ProductionConfig)


def test_production_requires_persistent_database(monkeypatch):
    class ProductionConfig:
        TESTING = False
        SECRET_KEY = "a-production-secret-key-with-at-least-32-characters"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="persistent PostgreSQL"):
        create_app(ProductionConfig)


def test_session_cookies_are_secure_by_default(monkeypatch):
    class SecureCookieConfig:
        TESTING = True
        SECRET_KEY = "test-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    app = create_app(SecureCookieConfig)
    assert app.config["SESSION_COOKIE_SECURE"] is True


def test_login_rejects_bad_credentials_and_owner_cannot_open_admin(app, client):
    make_tenant(app)
    response = client.post("/login", data={"email": "store-a@example.com", "password": "wrong"})
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data
    login_owner(client)
    assert client.get("/admin/", base_url="http://store-a.test").status_code == 403


def test_admin_business_provisioning_creates_owner_categories_and_settings(app, client):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="SUPER_ADMIN")
        admin.set_password("secret123")
        db.session.add(admin)
        db.session.commit()
    client.post("/login", data={"email": "admin@example.com", "password": "secret123"})
    assert client.get("/admin/").status_code == 200
    response = client.post("/admin/businesses", data={
        "name": "New Atelier",
        "slug": "new-atelier",
        "description": "A electronics studio",
        "owner_name": "A Owner",
        "owner_email": "owner@atelier.example",
        "owner_phone": "123",
        "contact_email": "hello@atelier.example",
        "address": "1 High Street",
        "whatsapp_number": "2348010000000",
        "domain": "",
        "status": "ACTIVE",
    })
    assert response.status_code == 302
    with app.app_context():
        business = Business.query.filter_by(slug="new-atelier").one()
        owner = User.query.filter_by(email="owner@atelier.example").one()
        assert owner.password_hash != "ChangeMe!2026"
        assert owner.check_password(owner.password_hash) is False
        assert Category.query.filter_by(business_id=business.id).count() == 18
        assert StoreSettings.query.filter_by(business_id=business.id).one()


def test_admin_business_edit_page_and_domain_page_render(app, client):
    business_id, owner_id = make_tenant(app)
    client.post("/login", data={"email": "admin@example.com", "password": "secret123"})
    assert client.get(f"/admin/businesses/{business_id}/edit").status_code == 200
    assert client.get("/admin/domains").status_code == 200


def test_unauthenticated_dashboard_redirects_to_login(client):
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert "/login" in response.location


def test_inactive_users_and_suspended_businesses_cannot_keep_sessions(app, client):
    business_id, owner_id = make_tenant(app)
    with app.app_context():
        db.session.get(User, owner_id).active = False
        db.session.commit()
    invalid_login = client.post("/login", data={
        "email": "store-a@example.com", "password": "secret123",
    }, base_url="http://store-a.test")
    assert b"Invalid email or password" in invalid_login.data
    with app.app_context():
        db.session.get(User, owner_id).active = True
        db.session.commit()
    login_owner(client)
    with app.app_context():
        db.session.get(Business, business_id).status = "SUSPENDED"
        db.session.commit()
    response = client.get("/dashboard/", base_url="http://store-a.test")
    assert response.status_code == 302
    assert "/login" in response.location


def test_domain_resolution_isolated_and_single_store_fallback(app, client):
    business_a, _ = make_tenant(app)
    business_b, _ = make_tenant(app, "Store B", "store-b", "store-b.test")
    product_a = make_product(app, business_a, name="A coat", slug="a-coat")
    product_b = make_product(app, business_b, name="B dress", slug="b-dress", gender="Women")

    response_a = client.get("/", base_url="http://store-a.test")
    response_b = client.get("/", base_url="http://store-b.test")
    response_unknown = client.get("/", base_url="http://unknown.test")
    assert b"A coat" in response_a.data and b"B dress" not in response_a.data
    assert b"B dress" in response_b.data and b"A coat" not in response_b.data
    assert b"A coat" in response_unknown.data and b"B dress" not in response_unknown.data
    assert client.get("/catalogue", base_url="http://store-a.test").status_code == 404


def test_owner_cannot_read_or_mutate_another_business_product_or_order(app, client):
    business_a, _ = make_tenant(app)
    business_b, _ = make_tenant(app, "Store B", "store-b", "store-b.test")
    product_b = make_product(app, business_b, name="Private dress", slug="private-dress")
    with app.app_context():
        customer = Customer(business_id=business_b, name="Other customer", phone="123")
        db.session.add(customer)
        db.session.flush()
        order = Order(
            business_id=business_b,
            customer_id=customer.id,
            reference="PRIVATE-ORDER",
            subtotal=10,
            total=10,
        )
        db.session.add(order)
        db.session.commit()
        order_id = order.id
        variant = ProductVariant(
            business_id=business_b,
            product_id=product_b,
            storage="M",
            colour="Blue",
            stock_quantity=4,
            is_available=True,
        )
        db.session.add(variant)
        db.session.commit()
    login_owner(client)
    assert client.get(f"/dashboard/products/{product_b}/edit", base_url="http://store-a.test").status_code == 404
    assert client.post(f"/dashboard/products/{product_b}/variants", data={
        "storage": "M", "colour": "Blue", "stock": "0", "available": "on",
    }, base_url="http://store-a.test").status_code == 404
    assert client.get(f"/dashboard/orders/{order_id}", base_url="http://store-a.test").status_code == 404
    assert client.get("/dashboard/orders", base_url="http://store-a.test").status_code == 200
    assert b"PRIVATE-ORDER" not in client.get("/dashboard/orders", base_url="http://store-a.test").data


def test_product_create_edit_publish_and_archive(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        category = Category(business_id=business_id, name="Shirts", slug="shirts", gender="Men")
        db.session.add(category)
        db.session.commit()
        category_id = category.id
    login_owner(client)
    create_response = client.post("/dashboard/products", data={
        "name": "Linen shirt",
        "slug": "linen-shirt",
        "description": "Lightweight fabric",
        "regular_price": "125.00",
        "discounted_price": "",
        "category_id": str(category_id),
        "gender": "Men",
        "electronics_type": "Ready-to-wear",
        "sku": "SHIRT-1",
        "is_published": "y",
    }, base_url="http://store-a.test")
    assert create_response.status_code == 302
    with app.app_context():
        product = Product.query.filter_by(business_id=business_id, slug="linen-shirt").one()
        product_id = product.id
        assert product.is_published
    edit_response = client.post(f"/dashboard/products/{product_id}/edit", data={
        "name": "Linen shirt updated",
        "slug": "linen-shirt",
        "description": "Updated description",
        "regular_price": "135.00",
        "discounted_price": "120.00",
        "category_id": str(category_id),
        "gender": "Men",
        "electronics_type": "Ready-to-wear",
        "sku": "SHIRT-1",
        "is_published": "y",
    }, base_url="http://store-a.test")
    assert edit_response.status_code == 302
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.name == "Linen shirt updated"
        assert product.price == 120
    archive = client.post(f"/dashboard/products/{product_id}/archive", base_url="http://store-a.test")
    assert archive.status_code == 302
    with app.app_context():
        assert db.session.get(Product, product_id).is_published is False


def test_single_product_image_is_saved_and_deleted(app, client):
    business_id, _ = make_tenant(app)
    login_owner(client)
    response = client.post("/dashboard/products", data={
        "name": "Photo Coat",
        "slug": "photo-coat",
        "regular_price": "150",
        "category_id": "0",
        "gender": "Women",
        "electronics_type": "Ready-to-wear",
        "is_published": "y",
        "images": (BytesIO(b"\xff\xd8\xff" + b"\x00" * 20), "front.jpg"),
    }, base_url="http://store-a.test", content_type="multipart/form-data")
    assert response.status_code == 302
    with app.app_context():
        product = Product.query.filter_by(business_id=business_id, slug="photo-coat").one()
        assert ProductImage.query.filter_by(product_id=product.id).count() == 1
        image_id = product.images[0].id
        assert all(image.image_data and image.mime_type for image in product.images)
    response = client.post(
        f"/dashboard/products/{product.id}/images/{image_id}/delete",
        base_url="http://store-a.test",
    )
    assert response.status_code == 302
    with app.app_context():
        remaining = ProductImage.query.filter_by(product_id=product.id).all()
        assert len(remaining) == 0


def test_discount_cannot_exceed_regular_price(app, client):
    make_tenant(app)
    login_owner(client)
    response = client.post("/dashboard/products", data={
        "name": "Bad discount", "slug": "bad-discount", "regular_price": "100",
        "discounted_price": "101", "category_id": "0", "gender": "Unisex",
        "electronics_type": "Ready-to-wear", "is_published": "y",
    }, base_url="http://store-a.test")
    assert response.status_code == 200
    assert b"Discounted price cannot exceed regular price" in response.data
    with app.app_context():
        assert Product.query.filter_by(slug="bad-discount").count() == 0


def test_variant_inventory_update_and_validation(app, client):
    business_id, _ = make_tenant(app)
    product_id = make_product(app, business_id)
    login_owner(client)
    response = client.post(f"/dashboard/products/{product_id}/variants", data={
        "storage": "M", "colour": "Wine", "sku": "LINEN-M-WINE",
        "price_override": "26000.00", "stock": "3", "available": "on",
    }, base_url="http://store-a.test")
    assert response.status_code == 302
    with app.app_context():
        variant = ProductVariant.query.one()
        variant_id = variant.id
        assert variant.stock_quantity == 3 and variant.price_override == 26000
    bad_response = client.post(f"/dashboard/products/{product_id}/variants", data={
        "storage": "M", "colour": "Wine", "stock": "-2",
    }, base_url="http://store-a.test")
    assert bad_response.status_code == 400
    with app.app_context():
        assert db.session.get(ProductVariant, variant_id).stock_quantity == 3


def test_categories_are_editable_and_cannot_delete_in_use(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        category = Category(business_id=business_id, name="Shirts", slug="shirts", gender="Men")
        db.session.add(category)
        db.session.commit()
        category_id = category.id
    make_product(app, business_id, category_id=category_id)
    login_owner(client)
    assert client.get("/dashboard/categories", base_url="http://store-a.test").status_code == 200
    response = client.post(f"/dashboard/categories/{category_id}/edit", data={
        "name": "Tops", "slug": "tops", "gender": "Men",
    }, base_url="http://store-a.test")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Category, category_id).name == "Tops"
    response = client.post(f"/dashboard/categories/{category_id}/delete", base_url="http://store-a.test")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Category, category_id) is not None


def test_storefront_filters_and_product_pages(app, client):
    business_id, _ = make_tenant(app)
    medium = make_product(app, business_id, name="Blue Coat", slug="blue-coat", gender="Women")
    other = make_product(app, business_id, name="Black Trousers", slug="black-trousers", gender="Men")
    with app.app_context():
        db.session.add_all([
            ProductVariant(business_id=business_id, product_id=medium, storage="M", colour="Blue",
                           stock_quantity=2, is_available=True),
            ProductVariant(business_id=business_id, product_id=other, storage="S", colour="Black",
                           stock_quantity=1, is_available=True),
        ])
        db.session.commit()
    home = client.get("/", base_url="http://store-a.test")
    assert home.status_code == 200
    assert b"Add to Cart" in home.data
    assert b"cart-nav-icon" in home.data
    assert b">Cart <" not in home.data
    collection = client.get("/collection", base_url="http://store-a.test")
    assert collection.status_code == 200
    assert b"Blue Coat" in collection.data and b"Black Trousers" in collection.data
    assert client.get("/catalogue", base_url="http://store-a.test").status_code == 404
    assert client.get("/product/blue-coat", base_url="http://store-a.test").status_code == 200
    assert client.get("/cart", base_url="http://store-a.test").status_code == 200
    login_owner(client)
    dashboard = client.get("/dashboard/", base_url="http://store-a.test")
    assert dashboard.status_code == 200


def test_cart_and_checkout_use_server_price_stock_and_snapshot(app, client):
    make_tenant(app)
    assert client.post("/cart/add", base_url="http://store-a.test").status_code == 404
    assert client.post("/checkout", base_url="http://store-a.test").status_code == 404


def test_cart_rejects_unavailable_variants_and_changed_stock(app, client):
    make_tenant(app)
    assert client.post("/cart/add", base_url="http://store-a.test").status_code == 404
    assert client.post("/cart/update", base_url="http://store-a.test").status_code == 404


def test_owner_can_change_profile_and_password(app, client):
    business_id, owner_id = make_tenant(app)
    login_owner(client)
    settings_page = client.get("/dashboard/settings", base_url="http://store-a.test")
    assert settings_page.status_code == 200 and b"Storefront brand editor" in settings_page.data
    settings_response = client.post("/dashboard/settings", data={
        "name": "My Updated Store",
        "description": "New description",
        "phone": "020000",
        "contact_email": "contact@example.com",
        "address": "1 Market Street",
        "whatsapp_number": "+234 801 222 3333",
        "brand_color": "#123456",
        "announcement": "New drop",
        "hero_title": "The collection",
        "about_text": "Made with care",
        "business_id": "9999",
        "logo": (BytesIO(b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 12), "store.webp"),
    }, base_url="http://store-a.test")
    assert settings_response.status_code == 302
    with app.app_context():
        business = db.session.get(Business, business_id)
        assert business.name == "My Updated Store"
        assert business.whatsapp_number == "+234 801 222 3333"
        assert business.logo_url == f"/media/businesses/{business_id}/logo"
        assert business.logo_data.startswith(b"RIFF") and business.logo_mime_type == "image/webp"
        assert StoreSettings.query.filter_by(business_id=business_id).one().hero_title == "The collection"
    password_response = client.post("/dashboard/account/password", data={
        "current_password": "secret123",
        "new_password": "correct horse battery",
        "confirm_password": "correct horse battery",
    }, base_url="http://store-a.test")
    assert password_response.status_code == 302
    bad_login = client.post("/login", data={
        "email": "store-a@example.com", "password": "secret123",
    }, base_url="http://store-a.test")
    assert b"Invalid email or password" in bad_login.data


def test_admin_password_reset_is_single_use(app, client):
    business_id, owner_id = make_tenant(app)
    client.post("/login", data={"email": "admin@example.com", "password": "secret123"})
    response = client.post(f"/admin/owners/{owner_id}/reset-password")
    assert response.status_code == 302
    page = client.get(response.location)
    match = re.search(rb"/reset-password/([A-Za-z0-9_-]+)", page.data)
    assert match
    reset_path = "/reset-password/" + match.group(1).decode("ascii")
    reset_response = client.post(reset_path, data={
        "password": "a much better password",
        "confirm_password": "a much better password",
    })
    assert reset_response.status_code == 302
    assert client.get(reset_path).status_code == 410
    with app.app_context():
        assert PasswordResetToken.query.one().used_at is not None
        assert db.session.get(User, owner_id).check_password("a much better password")


def test_owner_order_filter_status_and_cancellation_restock(app, client):
    business_id, _ = make_tenant(app)
    product_id = make_product(app, business_id)
    with app.app_context():
        customer = Customer(business_id=business_id, name="Ada Customer", phone="123456")
        variant = ProductVariant(business_id=business_id, product_id=product_id, storage="M", colour="Cream",
                                 stock_quantity=0, is_available=False)
        db.session.add_all([customer, variant])
        db.session.flush()
        order = Order(business_id=business_id, customer_id=customer.id, reference="ORDER-ABC",
                      subtotal=100, total=100, status="WHATSAPP_CHECKOUT_INITIATED")
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(business_id=business_id, order_id=order.id, product_id=product_id,
                                 variant_id=variant.id, product_name="Linen Shirt", storage="M", colour="Cream",
                                 quantity=2, unit_price=50, line_total=100))
        order_id = order.id
        variant_id = variant.id
        db.session.commit()
    login_owner(client)
    listing = client.get("/dashboard/orders?q=ORDER-ABC&status=WHATSAPP_CHECKOUT_INITIATED",
                         base_url="http://store-a.test")
    assert b"ORDER-ABC" in listing.data
    assert b"ORDER-ABC" not in client.get("/dashboard/orders?q=missing", base_url="http://store-a.test").data
    response = client.post(f"/dashboard/orders/{order_id}", data={
        "status": "CANCELLED", "internal_notes": "Customer cancelled",
    }, base_url="http://store-a.test")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(ProductVariant, variant_id).stock_quantity == 2
        assert db.session.get(ProductVariant, variant_id).is_available
        assert db.session.get(Order, order_id).status == "CANCELLED"
    assert client.post(f"/dashboard/orders/{order_id}", data={
        "status": "CONFIRMED", "internal_notes": "",
    }, base_url="http://store-a.test").status_code == 400


def test_domain_validation_and_manual_verification(app, client, monkeypatch):
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    business_id, _ = make_tenant(app)
    client.post("/login", data={"email": "admin@example.com", "password": "secret123"})
    bad = client.post("/admin/domains", data={
        "business_id": str(business_id), "host": "https://127.0.0.1",
    })
    assert bad.status_code == 200
    good = client.post("/admin/domains", data={
        "business_id": str(business_id), "host": "SHOP.Example.com",
    })
    assert good.status_code == 302
    with app.app_context():
        domain = Domain.query.filter_by(host="shop.example.com").one()
        domain_id = domain.id
        assert domain.status == "PENDING" and domain.provider_status == "MANUAL"
    assert client.get("/catalogue", base_url="http://shop.example.com").status_code == 404
    unconfirmed = client.post(f"/admin/domains/{domain_id}/verify")
    assert unconfirmed.status_code == 302
    with app.app_context():
        assert db.session.get(Domain, domain_id).status == "PENDING"
    confirmed = client.post(f"/admin/domains/{domain_id}/verify", data={"render_verified": "yes"})
    assert confirmed.status_code == 302
    with app.app_context():
        domain = db.session.get(Domain, domain_id)
        assert domain.status == "CONNECTED" and domain.verified_at is not None
    monkeypatch.setattr("app.routes.admin._tls_is_valid", lambda host: True)
    ssl_check = client.post(f"/admin/domains/{domain_id}/ssl-check")
    assert ssl_check.status_code == 302
    with app.app_context():
        assert db.session.get(Domain, domain_id).ssl_status == "ACTIVE"
    assert client.get("/", base_url="http://shop.example.com").status_code == 200
    suspended = client.post(f"/admin/domains/{domain_id}/suspend")
    assert suspended.status_code == 302
    assert client.get("/", base_url="http://shop.example.com").status_code == 404
    assert b"Reactivate" in client.get("/admin/domains").data
    reactivated = client.post(f"/admin/domains/{domain_id}/reactivate")
    assert reactivated.status_code == 302
    with app.app_context():
        domain = db.session.get(Domain, domain_id)
        assert domain.status == "PENDING" and domain.verified_at is None
    assert client.get("/catalogue", base_url="http://shop.example.com").status_code == 404


def test_render_api_domain_is_not_connected_until_provider_verifies(app, client, monkeypatch):
    business_id, _ = make_tenant(app)
    monkeypatch.setenv("RENDER_API_KEY", "not-a-real-key")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")
    monkeypatch.setattr("app.render_api.add_custom_domain", lambda host: {
        "id": "rnd-domain-123", "name": host, "verificationStatus": "unverified",
    })
    verification = {"status": "unverified"}
    monkeypatch.setattr("app.render_api.verify_custom_domain", lambda domain_id: None)
    monkeypatch.setattr("app.render_api.get_custom_domain", lambda domain_id: {
        "id": domain_id, "name": "api.example.com", "verificationStatus": verification["status"],
    })
    client.post("/login", data={"email": "admin@example.com", "password": "secret123"})
    response = client.post("/admin/domains", data={
        "business_id": str(business_id), "host": "api.example.com",
    })
    assert response.status_code == 302
    with app.app_context():
        domain = Domain.query.filter_by(host="api.example.com").one()
        domain_id = domain.id
        assert domain.render_domain_id == "rnd-domain-123"
        assert domain.status == "PENDING"
    response = client.post(f"/admin/domains/{domain_id}/verify")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Domain, domain_id).status == "PENDING"
    verification["status"] = "verified"
    response = client.post(f"/admin/domains/{domain_id}/refresh")
    assert response.status_code == 302
    with app.app_context():
        domain = db.session.get(Domain, domain_id)
        assert domain.status == "CONNECTED"
        assert domain.provider_status == "VERIFIED"
        assert domain.verified_at is not None


def test_domain_normalization():
    assert normalize_domain(" SHOP.Example.com. ") == "shop.example.com"
    assert normalize_domain("münich.example") == "xn--mnich-kva.example"
    for invalid in ("https://example.com", "127.0.0.1", "bad host.example", "example"):
        with pytest.raises(ValueError):
            normalize_domain(invalid)


def test_local_image_upload_serve_and_delete(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    valid_png = FileStorage(stream=BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 12), filename="test.png")
    validate_image(valid_png)
    invalid = FileStorage(stream=BytesIO(b"<html>not an image"), filename="bad.png")
    with pytest.raises(ValueError, match="valid JPEG"):
        validate_image(invalid)

    with app.test_request_context():
        image_url, storage_key = upload_image(valid_png, "electronics-catalogue/1/products/2")
    assert image_url.startswith("/media/")
    image_path = tmp_path / storage_key
    assert image_path.is_file()
    response = app.test_client().get(image_url)
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    with app.app_context():
        delete_image(storage_key)
    assert not image_path.exists()


def test_product_and_variant_deletion_preserve_order_history(app, client):
    business_id, _ = make_tenant(app)
    deletable_id = make_product(app, business_id, name="Unused item", slug="unused-item")
    protected_id = make_product(app, business_id, name="Ordered item", slug="ordered-item")
    with app.app_context():
        variant = ProductVariant(
            business_id=business_id, product_id=protected_id, storage="M", colour="Black",
            stock_quantity=2, is_available=True,
        )
        db.session.add(variant)
        db.session.flush()
        customer = Customer(business_id=business_id, name="Buyer", phone="2348000000000")
        db.session.add(customer)
        db.session.flush()
        order = Order(
            business_id=business_id, customer_id=customer.id, reference="ORDER-KEEP",
            subtotal=100, total=100,
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(
            business_id=business_id, order_id=order.id, product_id=None, variant_id=variant.id,
            product_name="Ordered item", storage="M", colour="Black", quantity=1,
            unit_price=100, line_total=100,
        ))
        variant_id = variant.id
        db.session.commit()
    login_owner(client)
    deleted = client.post(f"/dashboard/products/{deletable_id}/delete", base_url="http://store-a.test")
    assert deleted.status_code == 302
    with app.app_context():
        assert db.session.get(Product, deletable_id) is None
    blocked_product = client.post(f"/dashboard/products/{protected_id}/delete", base_url="http://store-a.test")
    blocked_variant = client.post(
        f"/dashboard/products/{protected_id}/variants/{variant_id}/delete",
        base_url="http://store-a.test",
    )
    assert blocked_product.status_code == 302
    assert blocked_variant.status_code == 302
    with app.app_context():
        assert db.session.get(Product, protected_id) is not None
        assert db.session.get(ProductVariant, variant_id) is not None



def test_owner_crud_changes_persist_in_database_after_restart(tmp_path):
    database_path = tmp_path / "catalogue.sqlite"
    database_uri = f"sqlite:///{database_path.as_posix()}"

    class PersistentConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = database_uri

    first_app = create_app(PersistentConfig)
    with first_app.app_context():
        db.create_all()
    client = first_app.test_client()
    business_id, _ = make_tenant(first_app)
    login_owner(client)

    created_category = client.post("/dashboard/categories", data={
        "name": "Everyday Wear", "slug": "everyday-wear", "gender": "Unisex",
    }, base_url="http://store-a.test")
    assert created_category.status_code == 302
    with first_app.app_context():
        category = Category.query.filter_by(business_id=business_id, slug="everyday-wear").one()
        category_id = category.id

    updated_category = client.post(f"/dashboard/categories/{category_id}/edit", data={
        "name": "Daily Essentials", "slug": "daily-essentials", "gender": "Unisex",
    }, base_url="http://store-a.test")
    assert updated_category.status_code == 302

    created_product = client.post("/dashboard/products", data={
        "name": "Classic Shirt", "slug": "classic-shirt",
        "description": "Database-backed product", "regular_price": "25000.00",
        "discounted_price": "22000.00", "category_id": str(category_id),
        "gender": "Unisex", "electronics_type": "Ready-to-wear", "sku": "CLASSIC-001",
        "is_published": "y",
    }, base_url="http://store-a.test")
    assert created_product.status_code == 302
    with first_app.app_context():
        product = Product.query.filter_by(business_id=business_id, slug="classic-shirt").one()
        product_id = product.id

    updated_product = client.post(f"/dashboard/products/{product_id}/edit", data={
        "name": "Classic Shirt Updated", "slug": "classic-shirt-updated",
        "description": "Updated in the owner dashboard", "regular_price": "30000.00",
        "discounted_price": "", "category_id": str(category_id),
        "gender": "Unisex", "electronics_type": "Ready-to-wear", "sku": "CLASSIC-002",
        "is_published": "y",
    }, base_url="http://store-a.test")
    assert updated_product.status_code == 302

    created_variant = client.post(f"/dashboard/products/{product_id}/variants", data={
        "storage": "M", "colour": "Black", "stock": "8", "price_override": "27500.00",
        "sku": "CLASSIC-M-BLK", "available": "on",
    }, base_url="http://store-a.test")
    assert created_variant.status_code == 302
    updated_variant = client.post(f"/dashboard/products/{product_id}/variants", data={
        "storage": "M", "colour": "Black", "stock": "12", "price_override": "28000.00",
        "sku": "CLASSIC-M-BLK-2", "available": "on",
    }, base_url="http://store-a.test")
    assert updated_variant.status_code == 302

    created_temporary = client.post("/dashboard/products", data={
        "name": "Temporary Product", "slug": "temporary-product",
        "description": "", "regular_price": "1000.00", "discounted_price": "",
        "category_id": "0", "gender": "Unisex", "electronics_type": "Ready-to-wear",
        "sku": "TEMP-001", "is_published": "y",
    }, base_url="http://store-a.test")
    assert created_temporary.status_code == 302
    with first_app.app_context():
        temporary = Product.query.filter_by(business_id=business_id, slug="temporary-product").one()
        temporary_id = temporary.id
    deleted_temporary = client.post(
        f"/dashboard/products/{temporary_id}/delete", base_url="http://store-a.test"
    )
    assert deleted_temporary.status_code == 302

    with first_app.app_context():
        db.session.remove()

    second_app = create_app(PersistentConfig)
    with second_app.app_context():
        category = db.session.get(Category, category_id)
        product = db.session.get(Product, product_id)
        variant = ProductVariant.query.filter_by(
            product_id=product_id, storage="M", colour="Black"
        ).one()
        assert category.name == "Daily Essentials"
        assert product.name == "Classic Shirt Updated"
        assert product.regular_price == 30000
        assert product.discounted_price is None
        assert product.category_id == category_id
        assert variant.stock_quantity == 12
        assert variant.price_override == 28000
        assert variant.sku == "CLASSIC-M-BLK-2"
        assert Product.query.filter_by(slug="temporary-product").count() == 0
        assert ActivityLog.query.filter_by(action="PRODUCT_CREATED").count() >= 2
        db.session.remove()


def test_csrf_is_required_outside_disabled_test_configuration():
    app = create_app(CsrfConfig)
    response = app.test_client().post("/login", data={"email": "admin@example.com", "password": "secret123"})
    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_database_image_storage_and_public_serving(app):
    business_id, _ = make_tenant(app)
    product_id = make_product(app, business_id)
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 12
    with app.app_context():
        business = db.session.get(Business, business_id)
        business.logo_data = image_bytes
        business.logo_mime_type = "image/png"
        business.logo_url = f"/media/businesses/{business_id}/logo"
        product_image = ProductImage(
            business_id=business_id,
            product_id=product_id,
            url="",
            image_data=image_bytes,
            mime_type="image/png",
            original_filename="catalogue.png",
            alt_text="Linen Shirt",
            sort_order=0,
        )
        db.session.add(product_image)
        db.session.flush()
        product_image.url = f"/media/products/{product_image.id}"
        image_url = product_image.url
        db.session.commit()
        image_id = product_image.id

    client = app.test_client()
    product_response = client.get(image_url)
    logo_response = client.get(f"/media/businesses/{business_id}/logo")
    assert product_response.status_code == 200
    assert product_response.data == image_bytes
    assert product_response.mimetype == "image/png"
    assert product_response.headers["X-Content-Type-Options"] == "nosniff"
    assert logo_response.status_code == 200
    assert logo_response.data == image_bytes

    with app.app_context():
        stored = db.session.get(ProductImage, image_id)
        assert stored.image_data == image_bytes
        assert stored.original_filename == "catalogue.png"


def test_database_image_upload_validation_rejects_overstoraged_or_invalid_files():
    from app.media import read_image

    invalid = FileStorage(stream=BytesIO(b"not-an-image"), filename="bad.png")
    with pytest.raises(ValueError, match="valid JPEG"):
        read_image(invalid)
    overstoraged = FileStorage(
        stream=BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024 + 1)),
        filename="large.png",
    )
    with pytest.raises(ValueError, match="5 MB"):
        read_image(overstoraged)


def test_owner_can_reassign_existing_product_photo_without_deleting_it(app):
    business_id, _ = make_tenant(app)
    original_product_id = make_product(app, business_id, name="Daviva", slug="daviva")
    target_product_id = make_product(app, business_id, name="Ankara", slug="ankara")
    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 12
    with app.app_context():
        image = ProductImage(
            business_id=business_id,
            product_id=original_product_id,
            url="/media/products/placeholder",
            image_data=image_bytes,
            mime_type="image/png",
            original_filename="ankara-fabric.png",
            alt_text="Daviva",
            sort_order=0,
        )
        db.session.add(image)
        db.session.commit()
        image_id = image.id

    client = app.test_client()
    login_owner(client)
    library = client.get("/dashboard/product-images", base_url="http://store-a.test")
    assert library.status_code == 200
    assert b"ankara-fabric.png" in library.data
    moved = client.post(
        f"/dashboard/product-images/{image_id}/assign",
        data={"product_id": str(target_product_id)},
        base_url="http://store-a.test",
    )
    assert moved.status_code == 302

    with app.app_context():
        stored = db.session.get(ProductImage, image_id)
        assert stored is not None
        assert stored.product_id == target_product_id
        assert stored.business_id == business_id
        assert stored.image_data == image_bytes
        assert stored.original_filename == "ankara-fabric.png"
        assert ProductImage.query.filter_by(id=image_id).count() == 1


def test_generic_store_bootstrap_creates_isolated_store_owner_and_defaults(app, monkeypatch):
    monkeypatch.setenv("STORE_NAME", "Northside Fashion")
    monkeypatch.setenv("STORE_SLUG", "northside-electronics")
    monkeypatch.setenv("STORE_DESCRIPTION", "Independent client catalogue")
    monkeypatch.setenv("STORE_OWNER_NAME", "Northside Owner")
    monkeypatch.setenv("STORE_OWNER_EMAIL", "owner@northside.example")
    monkeypatch.setenv("STORE_OWNER_PASSWORD", "a-unique-client-password")
    monkeypatch.setenv("STORE_CONTACT_EMAIL", "hello@northside.example")
    monkeypatch.setenv("STORE_WHATSAPP_NUMBER", "2348012345678")

    result = app.test_cli_runner().invoke(args=["bootstrap-store"])
    assert result.exit_code == 0, result.output

    with app.app_context():
        business = Business.query.filter_by(slug="northside-electronics").one()
        owner = User.query.filter_by(email="owner@northside.example").one()
        assert business.name == "Northside Fashion"
        assert business.description == "Independent client catalogue"
        assert business.contact_email == "hello@northside.example"
        assert business.whatsapp_number == "2348012345678"
        assert owner.business_id == business.id
        assert owner.role == "OWNER"
        assert owner.check_password("a-unique-client-password")
        assert StoreSettings.query.filter_by(business_id=business.id).one()
        assert Category.query.filter_by(business_id=business.id).count() == 18


def test_generic_store_bootstrap_is_idempotent_and_never_resets_password(app, monkeypatch):
    monkeypatch.setenv("STORE_NAME", "Repeat Store")
    monkeypatch.setenv("STORE_SLUG", "repeat-store")
    monkeypatch.setenv("STORE_OWNER_NAME", "Repeat Owner")
    monkeypatch.setenv("STORE_OWNER_EMAIL", "repeat@example.com")
    monkeypatch.setenv("STORE_OWNER_PASSWORD", "first-password-is-unique")

    runner = app.test_cli_runner()
    first = runner.invoke(args=["bootstrap-store"])
    assert first.exit_code == 0, first.output

    with app.app_context():
        owner = User.query.filter_by(email="repeat@example.com").one()
        original_hash = owner.password_hash

    monkeypatch.setenv("STORE_OWNER_PASSWORD", "second-password-is-different")
    second = runner.invoke(args=["bootstrap-store"])
    assert second.exit_code == 0, second.output

    with app.app_context():
        assert Business.query.filter_by(slug="repeat-store").count() == 1
        assert User.query.filter_by(email="repeat@example.com").count() == 1
        owner = User.query.filter_by(email="repeat@example.com").one()
        assert owner.password_hash == original_hash
        assert owner.check_password("first-password-is-unique")
        assert not owner.check_password("second-password-is-different")
        assert StoreSettings.query.filter_by(business_id=owner.business_id).count() == 1
        assert Category.query.filter_by(business_id=owner.business_id).count() == 18


def test_generic_store_bootstrap_rejects_owner_email_used_by_another_store(app, monkeypatch):
    make_tenant(app, "Existing Store", "existing-store", "existing-store.test")
    monkeypatch.setenv("STORE_NAME", "New Store")
    monkeypatch.setenv("STORE_SLUG", "new-store")
    monkeypatch.setenv("STORE_OWNER_NAME", "New Owner")
    monkeypatch.setenv("STORE_OWNER_EMAIL", "existing-store@example.com")
    monkeypatch.setenv("STORE_OWNER_PASSWORD", "a-new-unique-password")

    result = app.test_cli_runner().invoke(args=["bootstrap-store"])
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert "already assigned to another account" in str(result.exception)

    with app.app_context():
        assert Business.query.filter_by(slug="new-store").count() == 0
        assert User.query.filter_by(email="existing-store@example.com").count() == 1


def test_generic_store_bootstrap_rejects_missing_or_weak_configuration(app, monkeypatch):
    for key in (
        "STORE_NAME", "STORE_SLUG", "STORE_OWNER_NAME", "STORE_OWNER_EMAIL",
        "STORE_OWNER_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    missing = app.test_cli_runner().invoke(args=["bootstrap-store"])
    assert missing.exit_code != 0
    assert isinstance(missing.exception, RuntimeError)
    assert "STORE_NAME" in str(missing.exception)

    monkeypatch.setenv("STORE_NAME", "Weak Password Store")
    monkeypatch.setenv("STORE_SLUG", "weak-password-store")
    monkeypatch.setenv("STORE_OWNER_NAME", "Owner")
    monkeypatch.setenv("STORE_OWNER_EMAIL", "weak@example.com")
    monkeypatch.setenv("STORE_OWNER_PASSWORD", "short")
    weak = app.test_cli_runner().invoke(args=["bootstrap-store"])
    assert weak.exit_code != 0
    assert isinstance(weak.exception, RuntimeError)
    assert "at least 12 characters" in str(weak.exception)


def test_storefront_home_shows_four_products_with_description_and_collection_link(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        category = Category(business_id=business_id, name="Shirts", slug="shirts", gender="Men")
        db.session.add(category)
        db.session.flush()
        for number in range(6):
            make_product(app, business_id, name=f"Shirt {number}", slug=f"shirt-{number}",
                         category_id=category.id, description="Soft cotton fabric")
    response = client.get("/", base_url="http://store-a.test")
    assert response.status_code == 200
    assert response.data.count(b"data-product-card") == 4
    assert b"Soft cotton fabric" in response.data
    assert b"/collection" in response.data


def test_collection_filters_by_tenant_category_and_cart_page_loads(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        shirts = Category(business_id=business_id, name="Shirts", slug="shirts", gender="Men")
        trousers = Category(business_id=business_id, name="Trousers", slug="trousers", gender="Men")
        db.session.add_all([shirts, trousers])
        db.session.flush()
        make_product(app, business_id, name="Oxford Shirt", slug="oxford-shirt", category_id=shirts.id)
        make_product(app, business_id, name="Chino Trousers", slug="chino-trousers", category_id=trousers.id)
        shirts_id = shirts.id
    response = client.get(f"/collection?category={shirts_id}", base_url="http://store-a.test")
    assert response.status_code == 200
    assert b"Oxford Shirt" in response.data
    assert b"Chino Trousers" not in response.data
    cart_response = client.get("/cart", base_url="http://store-a.test")
    assert cart_response.status_code == 200
    assert b"store-cart-drawer" in cart_response.data
    assert b"Your cart" in cart_response.data
    assert b"Your bag" not in cart_response.data


def test_collection_deduplicates_category_labels_and_filters_all_same_name_categories(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        first = Category(business_id=business_id, name="Accessories", slug="accessories", gender="Unisex")
        duplicate = Category(business_id=business_id, name=" accessories ", slug="accessories-2", gender="Unisex")
        db.session.add_all([first, duplicate])
        db.session.flush()
        make_product(app, business_id, name="Leather Bag", slug="leather-bag", category_id=first.id)
        make_product(app, business_id, name="Silk Scarf", slug="silk-scarf", category_id=duplicate.id)
        first_id = first.id
    response = client.get("/collection", base_url="http://store-a.test")
    assert response.status_code == 200
    assert response.data.count(b"Accessories") == 1
    filtered = client.get(f"/collection?category={first_id}", base_url="http://store-a.test")
    assert filtered.status_code == 200
    assert b"Leather Bag" in filtered.data
    assert b"Silk Scarf" in filtered.data


def test_owner_can_choose_product_cover_without_deleting_gallery_images(app, client):
    business_id, _ = make_tenant(app)
    product_id = make_product(app, business_id, name="Linen Set", slug="linen-set")
    with app.app_context():
        first = ProductImage(
            business_id=business_id, product_id=product_id, url="/media/products/first",
            image_data=b"first", mime_type="image/jpeg", original_filename="wrong-screenshot.jpg",
            alt_text="Linen Set", sort_order=0,
        )
        second = ProductImage(
            business_id=business_id, product_id=product_id, url="/media/products/second",
            image_data=b"second", mime_type="image/jpeg", original_filename="linen-set-front.jpg",
            alt_text="Linen Set", sort_order=1,
        )
        db.session.add_all([first, second])
        db.session.commit()
        second_id = second.id
    login_owner(client)
    response = client.post(
        f"/dashboard/products/{product_id}/images/{second_id}/cover",
        base_url="http://store-a.test",
    )
    assert response.status_code == 302
    with app.app_context():
        images = ProductImage.query.filter_by(product_id=product_id).order_by(
            ProductImage.sort_order, ProductImage.id
        ).all()
        assert [image.original_filename for image in images] == [
            "linen-set-front.jpg", "wrong-screenshot.jpg"
        ]
        assert len(images) == 2



def test_owner_dashboard_shows_only_core_catalogue_tools(app, client):
    make_tenant(app)
    login_owner(client)
    response = client.get("/dashboard/", base_url="http://store-a.test")
    assert response.status_code == 200
    for label in [b"Products", b"Categories", b"Store information", b"Change password", b"Recently updated products"]:
        assert label in response.data
    # "Customers" appears in the explanatory sentence about who can browse the shop;
    # assert the removed dashboard navigation labels are absent as standalone items.
    for removed_label in [b">Recent orders<", b">Customers<", b">Photo library<", b">Domain management<"]:
        assert removed_label not in response.data


def test_storefront_footer_back_to_top_is_in_page_anchor(app, client):
    make_tenant(app)
    response = client.get("/", base_url="http://store-a.test")
    assert response.status_code == 200
    assert b'<body id="top"' in response.data
    assert b'href="#top">Back to top' in response.data


def test_add_product_page_exposes_electronics_fields_and_saves_them(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        category = Category(business_id=business_id, name="Smartphones", slug="smartphones", gender="Phones")
        db.session.add(category)
        db.session.commit()
        category_id = category.id
    login_owner(client)
    page = client.get("/dashboard/products", base_url="http://store-a.test")
    assert page.status_code == 200
    for label in [b"Category", b"Compatibility", b"Device condition", b"RAM / storage configurations"]:
        assert label in page.data
    response = client.post("/dashboard/products", data={
        "name": "Galaxy S24", "slug": "galaxy-s24", "regular_price": "850000",
        "discounted_price": "", "category_id": str(category_id), "gender": "Android",
        "electronics_type": "Refurbished", "sku": "SAM-S24", "is_published": "y",
        "storages": "256GB, 512GB", "colours": "Black, Violet",
    }, base_url="http://store-a.test")
    assert response.status_code == 302
    with app.app_context():
        product = Product.query.filter_by(business_id=business_id, slug="galaxy-s24").one()
        assert product.category_id == category_id
        assert product.gender == "Android"
        assert product.electronics_type == "Refurbished"
        assert product.is_published
        assert ProductVariant.query.filter_by(product_id=product.id).count() == 4


def test_edit_product_updates_category_compatibility_and_condition(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        category = Category(business_id=business_id, name="Laptops", slug="laptops", gender="Computing")
        db.session.add(category)
        db.session.flush()
        product = Product(business_id=business_id, name="Laptop", slug="laptop", regular_price=650000)
        db.session.add(product)
        db.session.commit()
        product_id, category_id = product.id, category.id
    login_owner(client)
    response = client.post(f"/dashboard/products/{product_id}/edit", data={
        "name": "Laptop", "slug": "laptop", "regular_price": "650000", "discounted_price": "",
        "category_id": str(category_id), "gender": "Windows", "electronics_type": "Used",
        "is_published": "y",
    }, base_url="http://store-a.test")
    assert response.status_code == 302
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.category_id == category_id
        assert product.gender == "Windows" and product.electronics_type == "Used"


def test_product_forms_do_not_show_featured_or_new_arrival_status(app, client):
    make_tenant(app)
    login_owner(client)
    response = client.get("/dashboard/products", base_url="http://store-a.test")
    assert response.status_code == 200
    assert b"Featured product" not in response.data
    assert b"New arrival" not in response.data
    assert b"Published" in response.data


def test_product_upload_accepts_only_one_image_and_replaces_existing_photo(app, client):
    business_id, _ = make_tenant(app)
    login_owner(client)
    response = client.get("/dashboard/products", base_url="http://store-a.test")
    assert b'Upload one clear product photo.' in response.data
    assert b'multiple' not in response.data
    assert b'up to 8' not in response.data.lower()


def test_footer_social_links_only_render_when_owner_configures_them(app, client):
    business_id, _ = make_tenant(app)
    response = client.get("/", base_url="http://store-a.test")
    assert response.status_code == 200
    assert b'aria-label="Facebook"' not in response.data
    assert b'aria-label="Instagram"' not in response.data
    assert b'aria-label="TikTok"' not in response.data
    assert b'aria-label="X"' not in response.data
    assert b'Get in touch' not in response.data
    html = response.data.decode()
    footer = html.split('<footer class="store-footer luxury-footer">', 1)[1].split('</footer>', 1)[0]
    assert 'WhatsApp' not in footer
    assert b'>Email ' not in response.data


def test_guest_wishlist_page_and_product_detail_routes(app, client):
    business_id, _ = make_tenant(app)
    category_id = None
    with app.app_context():
        category = Category(business_id=business_id, name="Agbada", slug="men-agbada", gender="Men")
        db.session.add(category)
        db.session.commit()
        category_id = category.id
    product_id = make_product(app, business_id, name="Royal Agbada", slug="royal-agbada", category_id=category_id)
    with app.app_context():
        product = Product.query.get(product_id)
        db.session.add_all([
            ProductImage(business_id=business_id, product_id=product_id, url="/media/products/101", sort_order=0),
            ProductImage(business_id=business_id, product_id=product_id, url="/media/products/102", sort_order=1),
            ProductImage(business_id=business_id, product_id=product_id, url="/media/products/103", sort_order=2),
            ProductImage(business_id=business_id, product_id=product_id, url="/media/products/999", sort_order=3),
        ])
        db.session.commit()
    detail = client.get("/product/royal-agbada", base_url="http://store-a.test")
    assert detail.status_code == 200
    assert b"Royal Agbada" in detail.data
    assert b"premium-product-layout" in detail.data
    assert b"product-breadcrumb" not in detail.data
    assert b"Secure Payment" not in detail.data
    assert b"Easy Returns" not in detail.data
    assert b"Storage Guide" not in detail.data
    assert b"/media/products/101" in detail.data
    assert b"/media/products/102" in detail.data
    assert b"/media/products/103" in detail.data
    assert b"/media/products/999" not in detail.data
    wishlist = client.get("/wishlist", base_url="http://store-a.test")
    assert wishlist.status_code == 200
    assert b"Saved for later" in wishlist.data


def test_category_route_is_scoped_and_pins_requested_product_first(app, client):
    business_id, _ = make_tenant(app)
    with app.app_context():
        agbada = Category(business_id=business_id, name="Agbada", slug="men-agbada", gender="Men")
        unrelated = Category(business_id=business_id, name="Shoes", slug="men-shoes", gender="Men")
        db.session.add_all([agbada, unrelated])
        db.session.commit()
        agbada_id, shoes_id = agbada.id, unrelated.id
    first_id = make_product(app, business_id, name="Agbada One", slug="agbada-one", category_id=agbada_id)
    pinned_id = make_product(app, business_id, name="Agbada Two", slug="agbada-two", category_id=agbada_id)
    make_product(app, business_id, name="Leather Shoes", slug="leather-shoes", category_id=shoes_id)
    response = client.get(f"/category/men-agbada?product={pinned_id}", base_url="http://store-a.test")
    assert response.status_code == 200
    body = response.data.decode()
    assert body.index("Agbada Two") < body.index("Agbada One")
    assert "Leather Shoes" not in body

def test_storefront_wishlist_opens_as_client_drawer_and_hearts_are_inside_product_photos(app, client):
    business_id, _ = make_tenant(app)
    make_product(app, business_id, name="Wishlist Test", slug="wishlist-test")
    home = client.get("/", base_url="http://store-a.test")
    collection = client.get("/collection", base_url="http://store-a.test")
    assert home.status_code == 200
    assert collection.status_code == 200
    assert b'data-wishlist-open' in home.data
    assert b'data-wishlist-drawer' in home.data
    assert b'data-wishlist-toggle' in home.data
    assert b'Shop by category' not in home.data
    assert b'category-shortcuts' not in collection.data



def test_storefront_visit_tracking_does_not_block_get_navigation(app, client):
    business_id, _ = make_tenant(app)
    response = client.get("/", base_url="http://store-a.test")
    assert response.status_code == 200
    with app.app_context():
        from app.models import StoreVisit
        assert StoreVisit.query.filter_by(business_id=business_id).count() == 0
    tracked = client.post(
        "/track-visit",
        json={"path": "/collection"},
        base_url="http://store-a.test",
    )
    assert tracked.status_code == 202
    with app.app_context():
        visit = StoreVisit.query.filter_by(business_id=business_id, path="/collection").one()
        assert visit is not None
