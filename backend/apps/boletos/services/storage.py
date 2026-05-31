from pathlib import Path

from django.utils import timezone
from slugify import slugify


def _safe_ext(filename: str) -> str:
    return Path(filename or "").suffix.lower()[:12]


def boleto_upload_path(instance, filename: str) -> str:
    now = timezone.localdate()
    ext = _safe_ext(filename)
    company_id = instance.company_id or "sem-empresa"
    return f"boletos/{company_id}/{now:%Y}/{now:%m}/{instance.pk}{ext}"


def preview_upload_path(instance, filename: str) -> str:
    now = timezone.localdate()
    ext = _safe_ext(filename) or ".jpg"
    company_id = instance.company_id or "sem-empresa"
    name = slugify(Path(filename or "preview").stem)[:40] or "preview"
    return f"boletos/{company_id}/{now:%Y}/{now:%m}/{instance.pk}-{name}{ext}"
