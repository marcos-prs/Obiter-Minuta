import io
import re
import pdfplumber
from app.utils.sanitizer import sanitize_text, remove_page_artifacts, clean_header_footer


CONVERTER_VERSION = "1.2.0"


def extract_text_pdfplumber(pdf_bytes: bytes) -> tuple[str, int]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
        full_text = "\n".join(pages)
        return sanitize_text(full_text), len(pdf.pages)


def convert_pdf_to_markdown(pdf_bytes: bytes) -> tuple[str, int]:
    raw_text, page_count = extract_text_pdfplumber(pdf_bytes)
    cleaned = remove_page_artifacts(raw_text)
    cleaned = clean_header_footer(cleaned)
    markdown = _text_to_markdown(cleaned)
    return markdown, page_count


def _text_to_markdown(text: str) -> str:
    lines = text.split("\n")
    md_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            md_lines.append("")
            in_list = False
            continue
        if _is_heading(stripped):
            level = _heading_level(stripped)
            md_lines.append(f"{'#' * level} {stripped}")
            in_list = False
        elif stripped.startswith("- ") or stripped.startswith("* "):
            md_lines.append(f"  {stripped}")
            in_list = True
        elif in_list:
            md_lines.append(f"    {stripped}")
        else:
            md_lines.append(stripped)
    return "\n".join(md_lines)


def _is_heading(line: str) -> bool:
    if len(line) < 3:
        return False
    upper_ratio = sum(1 for c in line if c.isupper()) / max(len(line) - sum(1 for c in line if not c.isalpha()), 1)
    if upper_ratio > 0.7 and len(line) < 80:
        return True
    patterns = [
        r"^(I{1,3}|IV|VI{0,3}|IX|X{1,3})\.",
        r"^[A-Z][\s]*[\.\-]\s",
        r"^(PRELIMINARES?|DOS FATOS|DO DIREITO|DOS PEDIDOS|DA TUTELA|RECURSO|CONTESTACAO)",
    ]
    return any(re.match(p, line, re.IGNORECASE) for p in patterns)


def _heading_level(line: str) -> int:
    if re.match(r"^(I{1,3}|IV|VI{0,3}|IX|X{1,3})\.", line):
        return 2
    if re.match(r"^[A-Z][\s]*[\.\-]\s", line):
        return 3
    return 2
