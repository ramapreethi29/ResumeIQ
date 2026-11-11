from pypdf import PdfReader
from docx import Document
from io import BytesIO
import re


def normalize_extracted_text(text: str) -> str:

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive horizontal whitespace while
    # preserving line breaks and section structure.
    lines = []

    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def extract_file_text(filename: str, file_bytes: bytes) -> str:

    extension = filename.lower().split(".")[-1]

    if extension == "pdf":

        pdf = PdfReader(BytesIO(file_bytes))

        text = "\n".join(
            page.extract_text(extraction_mode="layout") or ""
            for page in pdf.pages
        )

        return normalize_extracted_text(text)

    elif extension == "docx":

        document = Document(BytesIO(file_bytes))

        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

        return normalize_extracted_text(text)

    else:
        raise ValueError(
            "Only PDF and DOCX files are supported."
        )