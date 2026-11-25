from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import deferred

from . import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Business(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    phone = db.Column(db.String(40))
    contact_email = db.Column(db.String(255))
    address = db.Column(db.Text)
    whatsapp_number = db.Column(db.String(40))
    logo_url = db.Column(db.String(500))
    logo_public_id = db.Column(db.String(255))
    # Keep binary assets out of ordinary Business queries; load only when serving the asset.
    logo_data = deferred(db.Column(db.LargeBinary))
    logo_mime_type = db.Column(db.String(50))
    banner_url = db.Column(db.String(500))
    banner_public_id = db.Column(db.String(255))
    banner_data = deferred(db.Column(db.LargeBinary))
    banner_mime_type = db.Column(db.String(50))
    brand_color = db.Column(db.String(7), default="#171717")
    status = db.Column(db.String(20), nullable=False, default="ACTIVE", index=True)
    users = db.relationship("User", back_populates="business", cascade="all, delete-orphan")
    domains = db.relationship("Domain", back_populates="business", cascade="all, delete-orphan")


class Domain(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    host = db.Column(db.String(255), unique=True, nullable=False, index=True)
    render_domain_id = db.Column(db.String(100))
    provider_status = db.Column(
        db.String(20),
        nullable=False,
        default="UNKNOWN",
        server_default="UNKNOWN",
    )
    is_primary = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    ssl_status = db.Column(db.String(20), nullable=False, default="PENDING")
    verified_at = db.Column(db.DateTime)
    business = db.relationship("Business", back_populates="domains")


class StoreSettings(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, unique=True)
    announcement = db.Column(db.String(255), default="Explore our latest phones, gadgets and accessories")
    hero_title = db.Column(db.String(180), default="Technology for every day, and everything ahead.")
    about_text = db.Column(db.Text)
    tagline = db.Column(db.String(160))
    hero_cta = db.Column(db.String(80))
    hero_whatsapp_cta = db.Column(db.String(80))
    proof1_title = db.Column(db.String(100))
    proof1_text = db.Column(db.String(180))
    proof2_title = db.Column(db.String(100))
    proof2_text = db.Column(db.String(180))
    proof3_title = db.Column(db.String(100))
    proof3_text = db.Column(db.String(180))
    catalogue_eyebrow = db.Column(db.String(100))
    catalogue_title = db.Column(db.String(180))
    empty_title = db.Column(db.String(180))
    empty_text = db.Column(db.String(500))
    order_eyebrow = db.Column(db.String(100))
    order_title = db.Column(db.String(180))
    order_text = db.Column(db.String(500))
    order_button = db.Column(db.String(100))
    nav_home = db.Column(db.String(50))
    nav_contact = db.Column(db.String(50))
    footer_text = db.Column(db.String(500))
    copyright_text = db.Column(db.String(180))
    instagram_url = db.Column(db.String(500))
    facebook_url = db.Column(db.String(500))
    tiktok_url = db.Column(db.String(500))
    x_url = db.Column(db.String(500))
    seo_title = db.Column(db.String(180))
    seo_description = db.Column(db.String(320))
    business = db.relationship("Business")


class User(db.Model, UserMixin, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=True, index=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(40))
    role = db.Column(db.String(20), nullable=False, default="OWNER")
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    business = db.relationship("Business", back_populates="users")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.active


class Category(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), nullable=False)
    gender = db.Column(db.String(20))
    business = db.relationship("Business")
    __table_args__ = (db.UniqueConstraint("business_id", "slug", name="uq_category_business_slug"),)


class Product(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    regular_price = db.Column(db.Numeric(12, 2), nullable=False)
    discounted_price = db.Column(db.Numeric(12, 2))
    gender = db.Column(db.String(20), nullable=False, default="Universal")
    electronics_type = db.Column(db.String(30), nullable=False, default="New")
    featured = db.Column(db.Boolean, default=False)
    new_arrival = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    sku = db.Column(db.String(100))
    business = db.relationship("Business")
    category = db.relationship("Category")
    images = db.relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="(ProductImage.sort_order, ProductImage.id)")
    variants = db.relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("business_id", "slug", name="uq_product_business_slug"),)

    @property
    def price(self):
        return self.discounted_price if self.discounted_price is not None else self.regular_price


class ProductImage(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    url = db.Column(db.String(500), nullable=False)
    cloudinary_public_id = db.Column(db.String(255))
    # Product listings need image metadata/URLs, not the full binary payload.
    image_data = deferred(db.Column(db.LargeBinary))
    mime_type = db.Column(db.String(50))
    original_filename = db.Column(db.String(255))
    alt_text = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0)
    product = db.relationship("Product", back_populates="images")


class ProductVariant(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    storage = db.Column(db.String(50), nullable=False)
    colour = db.Column(db.String(50), nullable=False)
    sku = db.Column(db.String(100))
    price_override = db.Column(db.Numeric(12, 2))
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    is_available = db.Column(db.Boolean, default=True)
    product = db.relationship("Product", back_populates="variants")
    __table_args__ = (
        db.UniqueConstraint("product_id", "storage", "colour", name="uq_variant_product_storage_colour"),
    )


class Customer(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    address = db.Column(db.Text)


class Order(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    reference = db.Column(db.String(40), unique=True, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="WHATSAPP_CHECKOUT_INITIATED", index=True)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    delivery_address = db.Column(db.Text)
    delivery_instructions = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    business = db.relationship("Business")
    customer = db.relationship("Customer")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variant.id"), nullable=True)
    product_name = db.Column(db.String(180), nullable=False)
    storage = db.Column(db.String(50), nullable=False)
    colour = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)
    order = db.relationship("Order", back_populates="items")


class StoreEvent(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=True, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True, index=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)


class PasswordResetToken(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    user = db.relationship("User")


class StoreVisit(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=False, index=True)
    path = db.Column(db.String(500))
    ip_hash = db.Column(db.String(64))


class ActivityLog(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("business.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text)


class AdminAuditLog(db.Model, TimestampMixin):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text)
