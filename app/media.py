from pathlib import Path
import time
from uuid import uuid4

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage


class MediaError(RuntimeError):
    pass


ALLOWED_IMAGE_TYPES = {
    "jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


def validate_image(file: FileStorage):
    if not file or not file.filename:
        raise ValueError("Choose an image file.")
    header = file.stream.read(12)
    file.stream.seek(0)
    if not any(signature(header) for signature in ALLOWED_IMAGE_TYPES.values()):
        raise ValueError("Use a valid JPEG, PNG or WebP image.")


def upload_image(file: FileStorage, folder: str):
    validate_image(file)
    parts = Path(folder).parts
    if not parts or any(part in {"", ".", ".."} for part in parts) or Path(folder).is_absolute():
        raise ValueError("Invalid image destination.")

    header = file.stream.read(12)
    file.stream.seek(0)
    extension = next(ext for ext, signature in ALLOWED_IMAGE_TYPES.items() if signature(header))
    relative_path = Path(*parts, f"{uuid4().hex}.{extension}")
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    destination = (upload_root / relative_path).resolve()
    if upload_root not in destination.parents:
        raise ValueError("Invalid image destination.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        file.save(destination)
    except OSError as error:
        raise MediaError("The image could not be saved. Check the upload storage configuration.") from error

    stored_key = relative_path.as_posix()
    return url_for("uploaded_media", filename=stored_key), stored_key


def delete_image(storage_key: str):
    if not storage_key:
        return
    relative_path = Path(storage_key)
    if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ValueError("Invalid image reference.")

    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    target = (upload_root / relative_path).resolve()
    if upload_root not in target.parents:
        raise ValueError("Invalid image reference.")
    for attempt in range(4):
        try:
            target.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt == 3:
                raise MediaError("The image could not be deleted from upload storage.")
            time.sleep(0.05)
        except OSError as error:
            raise MediaError("The image could not be deleted from upload storage.") from error


IMAGE_MIME_TYPES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


def read_image(file: FileStorage, max_bytes=5 * 1024 * 1024):
    """Read and validate an image for storage in the relational database."""
    if not file or not file.filename:
        raise ValueError("Choose an image file.")
    data = file.stream.read(max_bytes + 1)
    file.stream.seek(0)
    if len(data) > max_bytes:
        raise ValueError("Each image must be 5 MB or smaller.")
    mime_type = next(
        (mime for mime, signature in IMAGE_MIME_TYPES.items() if signature(data)),
        None,
    )
    if not mime_type:
        raise ValueError("Use a valid JPEG, PNG or WebP image.")
    return data, mime_type, Path(file.filename).name[:255]
