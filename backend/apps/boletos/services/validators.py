import hashlib
import re
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError


PDF_MAX_BYTES = getattr(settings, "BOLETOS_MAX_PDF_SIZE", 15 * 1024 * 1024)
IMAGE_MAX_BYTES = getattr(settings, "BOLETOS_MAX_IMAGE_SIZE", 10 * 1024 * 1024)
PDF_MAX_PAGES = getattr(settings, "BOLETOS_MAX_PDF_PAGES", 3)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
CONTENT_TYPES = {
    "pdf": {"application/pdf"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "webp": {"image/webp"},
}


def _extension(filename: str) -> str:
    return Path(filename or "").suffix.lower().lstrip(".")


def _magic_type(header: bytes) -> str | None:
    if header.startswith(b"%PDF"):
        return "pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def _read_file(uploaded_file) -> bytes:
    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return data


def validate_boleto_file(uploaded_file) -> dict:
    if not uploaded_file:
        raise ValidationError({"arquivo": "Arquivo é obrigatório."})

    data = _read_file(uploaded_file)
    size = len(data)
    if size == 0:
        raise ValidationError({"arquivo": "Arquivo vazio não é permitido."})

    ext = _extension(uploaded_file.name)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError({"arquivo": "Formato não permitido."})

    content_type = getattr(uploaded_file, "content_type", "") or ""
    if content_type not in CONTENT_TYPES[ext]:
        raise ValidationError({"content_type": "Content-Type inválido para o arquivo."})

    magic = _magic_type(data[:16])
    if magic is None:
        raise ValidationError({"arquivo": "Assinatura do arquivo inválida."})
    if ext in {"jpg", "jpeg"} and magic != "jpeg":
        raise ValidationError({"arquivo": "MIME real incompatível com extensão."})
    if ext not in {"jpg", "jpeg"} and magic != ext:
        raise ValidationError({"arquivo": "MIME real incompatível com extensão."})

    if ext == "pdf":
        if size > PDF_MAX_BYTES:
            raise ValidationError({"arquivo": "PDF excede o tamanho máximo de 15 MB."})
        if b"/Encrypt" in data[: min(size, 1024 * 1024)]:
            raise ValidationError({"arquivo": "PDF criptografado não é permitido na V1."})
        pages = max(1, len(re.findall(rb"/Type\s*/Page\b", data)))
        if pages > PDF_MAX_PAGES:
            raise ValidationError({"arquivo": f"PDF excede o limite de {PDF_MAX_PAGES} páginas."})
    else:
        if size > IMAGE_MAX_BYTES:
            raise ValidationError({"arquivo": "Imagem excede o tamanho máximo de 10 MB."})
        pages = 1

    return {
        "tipo_arquivo": "JPG" if ext == "jpg" else ext.upper(),
        "content_type": content_type,
        "tamanho_bytes": size,
        "sha256": hashlib.sha256(data).hexdigest(),
        "preview_pages": pages if ext == "pdf" else 1,
    }
