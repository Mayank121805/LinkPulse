import io
import base64
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask

def generate_qr_bytes(
    url: str,
    box_size: int = 10,
    border: int = 2,
    fill_color: tuple = (15, 23, 42), # Midnight navy #0F172A
    back_color: tuple = (255, 255, 255)
) -> bytes:
    """Generates PNG image bytes for a given destination/short URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

def generate_qr_data_uri(url: str, box_size: int = 8) -> str:
    """Generates base64 data URI for inline display in HTML img src tags."""
    png_bytes = generate_qr_bytes(url, box_size=box_size)
    encoded = base64.b64encode(png_bytes).decode('utf-8')
    return f"data:image/png;base64,{encoded}"
