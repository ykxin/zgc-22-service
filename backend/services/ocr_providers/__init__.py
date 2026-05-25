"""OCR provider registry."""
from services.ocr_providers.mock import MockQualificationOcrProvider


def get_ocr_provider():
    """Return the configured OCR provider.

    The project currently ships with a deterministic local mock. Real OCR vendors
    can be introduced by swapping this factory without changing API code.
    """
    return MockQualificationOcrProvider()
