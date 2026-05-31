from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings


class OCRError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OCRResult:
    text: str
    payload: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None


class OCRProvider(Protocol):
    name: str

    def extract_text_from_file(self, file_path: str) -> OCRResult:
        ...


class FakeOCRProvider:
    name = "FAKE"

    def extract_text_from_file(self, file_path: str) -> OCRResult:
        configured = getattr(settings, "BOLETOS_FAKE_OCR_TEXT", "")
        if configured:
            text = configured
        else:
            path = Path(file_path)
            data = path.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
        return OCRResult(
            text=text,
            payload={"provider": self.name, "characters": len(text)},
            raw_response={"fake": True},
            confidence=80.0 if text else 0.0,
        )


class GoogleVisionOCRProvider:
    name = "GOOGLE_VISION"

    def extract_text_from_file(self, file_path: str) -> OCRResult:
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise OCRError(
                "GOOGLE_VISION_UNAVAILABLE",
                "google-cloud-vision não está instalado no ambiente.",
            ) from exc

        path = Path(file_path)
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=path.read_bytes())
        response = client.document_text_detection(image=image)
        if response.error.message:
            raise OCRError("GOOGLE_VISION_ERROR", response.error.message)

        annotation = response.full_text_annotation
        text = annotation.text if annotation else ""
        pages = len(annotation.pages) if annotation else 0
        return OCRResult(
            text=text,
            payload={"provider": self.name, "pages": pages, "characters": len(text)},
            raw_response={"text": text, "pages": pages},
            confidence=None,
        )


def get_ocr_provider() -> OCRProvider:
    provider = str(getattr(settings, "BOLETOS_OCR_PROVIDER", "FAKE")).upper()
    if provider == "GOOGLE_VISION":
        return GoogleVisionOCRProvider()
    return FakeOCRProvider()
