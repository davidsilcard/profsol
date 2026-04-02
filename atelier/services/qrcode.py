from __future__ import annotations

import base64
from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage


def build_qr_code_data_uri(url: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    buffer = BytesIO()
    qr.make_image(image_factory=SvgPathImage).save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
