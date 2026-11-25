import hashlib
import os
import secrets
import socket
import ssl
from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import FileField, StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from .. import db
from ..media import read_image
from ..models import AdminAuditLog, Business, Category, Domain, Order, PasswordResetToken, Product, StoreEvent, StoreSettings, StoreVisit, User, utcnow
from .. import render_api
from ..render_api import RenderApiError
from ..security import roles_required
from ..utils import normalize_domain, slugify


bp = Blueprint("admin", __name__, url_prefix="/admin")


class BusinessForm(FlaskForm):
    name = StringField("Business name", validators=[DataRequired(), Length(max=160)])
    slug = StringField("Business slug", validators=[DataRequired(), Length(max=160), Regexp(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")])
    description = TextAreaField("Description")
    owner_name = StringField("Owner name", validators=[DataRequired(), Length(max=160)])
    owner_email = StringField("Owner email", validators=[DataRequired(), Email()])
    owner_phone = StringField("Owner phone")
    contact_email = StringField("Contact email", validators=[Optional(), Email(), Length(max=255)])
    address = TextAreaField("Business address")
    whatsapp_number = StringField(
        "WhatsApp number",
        validators=[Optional(), Regexp(r"^\+?[0-9][0-9\s().-]{5,38}$")],
    )
    logo = FileField("Business logo")
    domain = StringField("Custom domain")
    status = SelectField("Status", choices=[("ACTIVE", "Active"), ("SUSPENDED", "Suspended"), ("ARCHIVED", "Archived")])
    submit = SubmitField("Save business")


class BusinessEditForm(FlaskForm):
    name = StringField("Business name", validators=[DataRequired(), Length(max=160)])
    slug = StringField("Business slug", validators=[DataRequired(), Length(max=160), Regexp(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")])
    description = TextAreaField("Description")
    phone = StringField("Phone")
    contact_email = StringField("Contact email", validators=[Optional(), Email(), Length(max=255)])
    address = TextAreaField("Business address")
    whatsapp_number = StringField("WhatsApp number")
    status = SelectField("Status", choices=[("ACTIVE", "Active"), ("SUSPENDED", "Suspended"), ("ARCHIVED", "Archived")])
    submit = SubmitField("Save business")


class DomainForm(FlaskForm):
    business_id = SelectField("Business", coerce=int, validators=[DataRequired()])
    host = StringField("Custom domain", validators=[DataRequired(), Length(max=253)])
    submit = SubmitField("Assign domain")


DEFAULT_CATEGORIES = {
    "Men": ["Shirts", "Trousers", "Native Wear", "Senator Outfits", "Agbada", "Kaftans", "Jackets", "Shoes", "Accessories"],
    "Women": ["Dresses", "Abayas", "Hijabs", "Jilbabs", "Two-Piece Outfits", "Skirts", "Blouses", "Trousers", "Accessories"],
}


def _tls_is_valid(host):
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=4) as connection:
            with context.wrap_socket(connection, server_hostname=host) as secured:
                return bool(secured.getpeercert())
    except (OSError, ssl.SSLError, TimeoutError):
        return False


@bp.route("/")
@roles_required("SUPER_ADMIN")
def dashboard():
    businesses = Business.query.order_by(Business.created_at.desc()).all()
    stats = {
        "businesses": Business.query.count(),
        "active": Business.query.filter_by(status="ACTIVE").count(),
        "suspended": Business.query.filter_by(status="SUSPENDED").count(),
        "products": Product.query.count(),
        "domains_connected": Domain.query.filter_by(status="CONNECTED").count(),
        "domains_pending": Domain.query.filter_by(status="PENDING").count(),
        "orders": Order.query.count(),
        "initiated_orders": Order.query.filter_by(status="WHATSAPP_CHECKOUT_INITIATED").count(),
        "confirmed_orders": Order.query.filter(Order.status.in_(["CONFIRMED", "PROCESSING", "READY_FOR_DELIVERY", "COMPLETED"])).count(),
        "visits": StoreVisit.query.count(),
        "whatsapp_clicks": StoreEvent.query.filter_by(event_type="WHATSAPP_CHECKOUT_CLICK").count(),
    }
    most_visited = db.session.query(
        Business.name,
        db.func.count(StoreVisit.id).label("visits"),
    ).join(StoreVisit, StoreVisit.business_id == Business.id).group_by(
        Business.id, Business.name
    ).order_by(db.func.count(StoreVisit.id).desc()).limit(5).all()
    recent_activity = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", businesses=businesses, stats=stats,
                           most_visited=most_visited, recent_activity=recent_activity)


@bp.route("/businesses", methods=["GET", "POST"])
@roles_required("SUPER_ADMIN")
def businesses():
    form = BusinessForm()
    if form.validate_on_submit():
        domain_host = None
        if form.domain.data.strip():
            try:
                domain_host = normalize_domain(form.domain.data)
            except ValueError as error:
                flash(str(error), "danger")
                return render_template("admin/businesses.html", form=form,
                                       businesses=Business.query.order_by(Business.created_at.desc()).all())
            if Domain.query.filter_by(host=domain_host).first():
                flash("That domain is already in use.", "danger")
                return render_template("admin/businesses.html", form=form,
                                       businesses=Business.query.order_by(Business.created_at.desc()).all())
        business_slug = slugify(form.slug.data)
        existing = Business.query.filter_by(slug=business_slug).first()
        if existing:
            flash("A business with that slug already exists.", "danger")
        elif User.query.filter_by(email=form.owner_email.data.strip().lower()).first():
            flash("An account with that owner email already exists.", "danger")
        else:
            business = Business(
                name=form.name.data.strip(),
                slug=business_slug,
                description=form.description.data,
                phone=form.owner_phone.data,
                contact_email=form.contact_email.data.strip().lower() if form.contact_email.data else None,
                address=form.address.data,
                whatsapp_number=form.whatsapp_number.data,
                status=form.status.data,
            )
            db.session.add(business)
            db.session.flush()
            logo = form.logo.data
            if logo and logo.filename:
                try:
                    business.logo_data, business.logo_mime_type, _filename = read_image(logo)
                    business.logo_url = url_for("business_logo", business_id=business.id)
                except (ValueError, RuntimeError) as error:
                    db.session.rollback()
                    flash(str(error), "danger")
                    return render_template("admin/businesses.html", form=form,
                                           businesses=Business.query.order_by(Business.created_at.desc()).all())
            temporary_password = secrets.token_urlsafe(18)
            owner = User(
                business_id=business.id,
                name=form.owner_name.data.strip(),
                email=form.owner_email.data.strip().lower(),
                phone=form.owner_phone.data,
                role="OWNER",
            )
            owner.set_password(temporary_password)
            db.session.add(owner)
            for gender, names in DEFAULT_CATEGORIES.items():
                for category_name in names:
                    db.session.add(Category(
                        business_id=business.id,
                        name=category_name,
                        slug=slugify(f"{gender}-{category_name}"),
                        gender=gender,
                    ))
            db.session.add(StoreSettings(business_id=business.id))
            if domain_host:
                try:
                    remote = render_api.add_custom_domain(domain_host) if render_api.is_configured() else None
                except RenderApiError as error:
                    db.session.rollback()
                    flash(str(error), "danger")
                    return render_template("admin/businesses.html", form=form,
                                           businesses=Business.query.order_by(Business.created_at.desc()).all())
                db.session.add(Domain(
                    business_id=business.id,
                    host=domain_host,
                    is_primary=True,
                    render_domain_id=remote.get("id") if remote else None,
                    provider_status=remote.get("verificationStatus", "unverified").upper() if remote else "MANUAL",
                ))
            db.session.add(AdminAuditLog(admin_id=current_user.id, action="BUSINESS_CREATED",
                                         details=f"Business {business.name}"))
            db.session.commit()
            flash(f"Business created. Temporary password: {temporary_password}", "warning")
            return redirect(url_for("admin.businesses"))
    businesses = Business.query.order_by(Business.created_at.desc()).all()
    return render_template("admin/businesses.html", form=form, businesses=businesses)


@bp.route("/businesses/<int:business_id>/edit", methods=["GET", "POST"])
@roles_required("SUPER_ADMIN")
def edit_business(business_id):
    business = db.get_or_404(Business, business_id)
    form = BusinessEditForm(obj=business)
    if form.validate_on_submit():
        slug = slugify(form.slug.data)
        collision = Business.query.filter(Business.slug == slug, Business.id != business.id).first()
        if collision:
            flash("That business slug is already in use.", "danger")
        else:
            business.name = form.name.data.strip()
            business.slug = slug
            business.description = form.description.data
            business.phone = form.phone.data
            business.contact_email = form.contact_email.data.strip().lower() if form.contact_email.data else None
            business.address = form.address.data
            business.whatsapp_number = form.whatsapp_number.data
            business.status = form.status.data
            db.session.add(AdminAuditLog(admin_id=current_user.id, action="BUSINESS_UPDATED",
                                         details=f"Business {business.id}: {business.status}"))
            db.session.commit()
            flash("Business updated.", "success")
            return redirect(url_for("admin.businesses"))
    owners = User.query.filter_by(business_id=business.id, role="OWNER").order_by(User.created_at).all()
    return render_template("admin/business_edit.html", form=form, business=business, owners=owners)


@bp.route("/domains", methods=["GET", "POST"])
@roles_required("SUPER_ADMIN")
def domains():
    form = DomainForm()
    businesses = Business.query.order_by(Business.name).all()
    form.business_id.choices = [(business.id, business.name) for business in businesses]
    if form.validate_on_submit():
        try:
            host = normalize_domain(form.host.data)
        except ValueError as error:
            flash(str(error), "danger")
        else:
            if Domain.query.filter_by(host=host).first():
                flash("That domain is already assigned.", "danger")
            else:
                try:
                    remote = render_api.add_custom_domain(host) if render_api.is_configured() else None
                except RenderApiError as error:
                    flash(str(error), "danger")
                    remote = False
                if remote is False:
                    return render_template("admin/domains.html", form=form,
                                           domains=Domain.query.order_by(Domain.created_at.desc()).all(),
                                           render_hostname=os.getenv("RENDER_SERVICE_HOSTNAME", "").strip().lower(),
                                           render_api_enabled=False)
                domain = Domain(
                    business_id=form.business_id.data,
                    host=host,
                    status="PENDING",
                    render_domain_id=remote.get("id") if remote else None,
                    provider_status=remote.get("verificationStatus", "unverified").upper() if remote else "MANUAL",
                )
                if not Domain.query.filter_by(business_id=form.business_id.data, is_primary=True).first():
                    domain.is_primary = True
                db.session.add(domain)
                db.session.add(AdminAuditLog(admin_id=current_user.id, action="DOMAIN_ASSIGNED",
                                             details=host))
                db.session.commit()
                flash("Domain assigned. Finish the Render and DNS setup before verifying it.", "success")
                return redirect(url_for("admin.domains"))
    items = Domain.query.order_by(Domain.created_at.desc()).all()
    render_hostname = os.getenv("RENDER_SERVICE_HOSTNAME", "").strip().lower()
    try:
        render_api_enabled = render_api.is_configured()
    except RenderApiError as error:
        render_api_enabled = False
        flash(str(error), "danger")
    return render_template("admin/domains.html", form=form, domains=items, render_hostname=render_hostname,
                           render_api_enabled=render_api_enabled)


@bp.route("/domains/<int:domain_id>/verify", methods=["POST"])
@roles_required("SUPER_ADMIN")
def verify_domain(domain_id):
    domain = db.get_or_404(Domain, domain_id)
    if domain.status == "SUSPENDED":
        flash("Reactivate the suspended domain before verifying it.", "danger")
        return redirect(url_for("admin.domains"))
    if domain.business.status != "ACTIVE":
        flash("Activate the business before connecting its domain.", "danger")
        return redirect(url_for("admin.domains"))
    try:
        if render_api.is_configured():
            if not domain.render_domain_id:
                remote = render_api.add_custom_domain(domain.host)
                domain.render_domain_id = remote["id"]
            render_api.verify_custom_domain(domain.render_domain_id)
            remote = render_api.get_custom_domain(domain.render_domain_id)
            provider_status = remote.get("verificationStatus", "unverified").upper()
            domain.provider_status = provider_status
            is_verified = provider_status == "VERIFIED"
        else:
            is_verified = request.form.get("render_verified") == "yes"
            if not is_verified:
                flash("Confirm the domain is verified in the Render Dashboard first.", "danger")
                return redirect(url_for("admin.domains"))
            domain.provider_status = "MANUAL_VERIFIED"
    except RenderApiError as error:
        flash(str(error), "danger")
        return redirect(url_for("admin.domains"))
    if not is_verified:
        domain.status = "PENDING"
        domain.verified_at = None
        db.session.commit()
        flash("Render DNS verification is still pending. The storefront remains unavailable on this domain.", "warning")
        return redirect(url_for("admin.domains"))
    domain.status = "CONNECTED"
    domain.verified_at = utcnow()
    domain.ssl_status = "PENDING"
    db.session.add(AdminAuditLog(admin_id=current_user.id, action="DOMAIN_VERIFIED",
                                 details=f"{domain.host}: operator confirmed Render dashboard verification"))
    db.session.commit()
    flash("Domain marked connected based on the administrator's Render Dashboard verification.", "success")
    return redirect(url_for("admin.domains"))


@bp.route("/domains/<int:domain_id>/refresh", methods=["POST"])
@roles_required("SUPER_ADMIN")
def refresh_domain(domain_id):
    domain = db.get_or_404(Domain, domain_id)
    try:
        if not render_api.is_configured() or not domain.render_domain_id:
            flash("This domain is not connected to the Render API.", "warning")
            return redirect(url_for("admin.domains"))
        remote = render_api.get_custom_domain(domain.render_domain_id)
    except RenderApiError as error:
        flash(str(error), "danger")
        return redirect(url_for("admin.domains"))
    domain.provider_status = remote.get("verificationStatus", "unverified").upper()
    if domain.provider_status == "VERIFIED" and domain.status != "SUSPENDED":
        domain.status = "CONNECTED"
        domain.verified_at = domain.verified_at or utcnow()
    elif domain.provider_status != "VERIFIED":
        domain.status = "PENDING"
        domain.verified_at = None
        domain.ssl_status = "PENDING"
    db.session.commit()
    flash(f"Render reports this domain as {domain.provider_status.lower()}.", "success")
    return redirect(url_for("admin.domains"))


@bp.route("/domains/<int:domain_id>/ssl-check", methods=["POST"])
@roles_required("SUPER_ADMIN")
def check_domain_ssl(domain_id):
    domain = db.get_or_404(Domain, domain_id)
    if domain.status != "CONNECTED" or not domain.verified_at:
        abort(400)
    domain.ssl_status = "ACTIVE" if _tls_is_valid(domain.host) else "FAILED"
    db.session.commit()
    if domain.ssl_status == "ACTIVE":
        flash("A valid HTTPS certificate was verified.", "success")
    else:
        flash("HTTPS certificate verification failed; SSL is not marked active.", "danger")
    return redirect(url_for("admin.domains"))


@bp.route("/domains/<int:domain_id>/primary", methods=["POST"])
@roles_required("SUPER_ADMIN")
def make_primary_domain(domain_id):
    domain = db.get_or_404(Domain, domain_id)
    Domain.query.filter_by(business_id=domain.business_id).update({"is_primary": False})
    domain.is_primary = True
    db.session.add(AdminAuditLog(admin_id=current_user.id, action="PRIMARY_DOMAIN_CHANGED",
                                 details=domain.host))
    db.session.commit()
    flash("Primary domain updated.", "success")
    return redirect(url_for("admin.domains"))


@bp.route("/domains/<int:domain_id>/suspend", methods=["POST"])
@roles_required("SUPER_ADMIN")
def suspend_domain(domain_id):
    domain = db.get_or_404(Domain, domain_id)
    domain.status = "SUSPENDED"
    domain.ssl_status = "PENDING"
    db.session.add(AdminAuditLog(admin_id=current_user.id, action="DOMAIN_SUSPENDED",
                                 details=domain.host))
    db.session.commit()
    flash("Domain suspended.", "success")
    return redirect(url_for("admin.domains"))


@bp.route("/domains/<int:domain_id>/reactivate", methods=["POST"])
@roles_required("SUPER_ADMIN")
def reactivate_domain(domain_id):
    domain = db.get_or_404(Domain, domain_id)
    domain.status = "PENDING"
    domain.ssl_status = "PENDING"
    domain.verified_at = None
    db.session.add(AdminAuditLog(admin_id=current_user.id, action="DOMAIN_REACTIVATED",
                                 details=domain.host))
    db.session.commit()
    flash("Domain reactivated as pending. Verify it again before serving traffic.", "success")
    return redirect(url_for("admin.domains"))


@bp.route("/owners/<int:user_id>/reset-password", methods=["POST"])
@roles_required("SUPER_ADMIN")
def issue_password_reset(user_id):
    owner = User.query.filter_by(id=user_id, role="OWNER").first_or_404()
    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=owner.id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=utcnow() + timedelta(minutes=30),
    )
    db.session.add(reset)
    db.session.add(AdminAuditLog(admin_id=current_user.id, action="PASSWORD_RESET_ISSUED",
                                 details=f"Owner user {owner.id}"))
    db.session.commit()
    reset_url = url_for("auth.reset_password", token=token)
    flash(f"One-time reset link (expires in 30 minutes): {reset_url}", "warning")
    return redirect(url_for("admin.edit_business", business_id=owner.business_id))
