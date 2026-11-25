import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class RenderApiError(RuntimeError):
    pass


def _configuration():
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")
    if not api_key and not service_id:
        return None
    if not api_key or not service_id:
        raise RenderApiError("Set both RENDER_API_KEY and RENDER_SERVICE_ID to enable Render domain management.")
    return api_key, service_id


def is_configured():
    return _configuration() is not None


def _request(method, path, payload=None):
    configuration = _configuration()
    if configuration is None:
        raise RenderApiError("Render API credentials are not configured.")
    api_key, _ = configuration
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        "https://api.render.com/v1" + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            data = response.read()
    except HTTPError as error:
        raise RenderApiError(f"Render API rejected the domain request (HTTP {error.code}).") from error
    except (URLError, TimeoutError) as error:
        raise RenderApiError("Render API could not be reached.") from error
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError as error:
        raise RenderApiError("Render API returned an invalid response.") from error


def _service_path():
    configuration = _configuration()
    if configuration is None:
        raise RenderApiError("Render API credentials are not configured.")
    _, service_id = configuration
    return f"/services/{quote(service_id, safe='')}/custom-domains"


def add_custom_domain(host):
    result = _request("POST", _service_path(), {"name": host})
    domains = result if isinstance(result, list) else [result]
    for domain in domains:
        if isinstance(domain, dict) and domain.get("name", "").lower() == host.lower():
            return domain
    raise RenderApiError("Render accepted the request but did not return the requested domain.")


def verify_custom_domain(domain_id_or_name):
    path = f"{_service_path()}/{quote(domain_id_or_name, safe='')}/verify"
    return _request("POST", path)


def get_custom_domain(domain_id_or_name):
    path = f"{_service_path()}/{quote(domain_id_or_name, safe='')}"
    return _request("GET", path)
