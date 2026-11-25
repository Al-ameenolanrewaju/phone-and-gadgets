from functools import wraps
from flask import abort, g, redirect, url_for
from flask_login import current_user


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def tenant_business_id():
    if not current_user.is_authenticated:
        abort(401)
    if current_user.role == "SUPER_ADMIN":
        return g.get("business_id")
    return current_user.business_id
