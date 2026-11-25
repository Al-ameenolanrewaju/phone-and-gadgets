import hashlib
import hmac

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from .. import db
from ..models import Business, PasswordResetToken, User, utcnow


bp = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Sign in")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=12, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Reset password")


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        business_active = (
            Business.query.filter_by(id=user.business_id, status="ACTIVE").first()
            if user and user.role == "OWNER"
            else True
        )
        if (user and user.active and user.role in {"OWNER", "SUPER_ADMIN"}
                and business_active
                and user.check_password(form.password.data)):
            login_user(user)
            if user.role == "SUPER_ADMIN":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("owner.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    reset = PasswordResetToken.query.filter_by(token_hash=token_hash, used_at=None).first()
    if not reset or reset.expires_at <= utcnow() or not reset.user.active:
        return render_template("auth/reset_password.html", form=ResetPasswordForm(), invalid=True), 410
    form = ResetPasswordForm()
    if form.validate_on_submit():
        if not hmac.compare_digest(reset.token_hash, token_hash):
            return render_template("auth/reset_password.html", form=form, invalid=True), 410
        reset.user.set_password(form.password.data)
        reset.used_at = utcnow()
        PasswordResetToken.query.filter(
            PasswordResetToken.user_id == reset.user_id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": utcnow()}, synchronize_session=False)
        db.session.commit()
        flash("Password reset. Sign in with your new password.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form, invalid=False)
