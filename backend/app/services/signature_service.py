from pathlib import Path
from io import BytesIO


def compose_signature(pdf_path: Path, signature_path: Path, output_path: Path) -> None:
    """Overlay signature image onto the last page of a PDF."""
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    # Create signature overlay
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    # Place signature at bottom-right area
    c.drawImage(str(signature_path), 400, 50, width=120, height=60, preserveAspectRatio=True, mask='auto')
    c.save()
    packet.seek(0)

    sig_pdf = PdfReader(packet)
    original = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for i, page in enumerate(original.pages):
        if i == len(original.pages) - 1:
            page.merge_page(sig_pdf.pages[0])
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(output_path), "wb") as f:
        writer.write(f)
