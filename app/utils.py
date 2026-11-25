import ipaddress
import re
import unicodedata


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DOMAIN_LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug


def normalize_domain(value):
    value = (value or "").strip().rstrip(".")
    if not value or len(value) > 253 or any(char in value for char in "/:@?#"):
        raise ValueError("Enter a valid domain name without a scheme, path or port.")
    try:
        host = value.encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise ValueError("Enter a valid internationalized domain name.") from error
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("A domain name cannot be an IP address.")
    labels = host.split(".")
    if len(labels) < 2 or any(not DOMAIN_LABEL_PATTERN.fullmatch(label) for label in labels):
        raise ValueError("Enter a valid domain name with at least two valid labels.")
    if len(labels[-1]) < 2:
        raise ValueError("The domain suffix must contain at least two characters.")
    return host
