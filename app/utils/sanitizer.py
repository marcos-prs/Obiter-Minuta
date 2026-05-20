import re


def sanitize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def remove_page_artifacts(text: str) -> str:
    text = re.sub(r"(?m)^\s*-\s*\d+\s*-$", "", text)
    text = re.sub(r"(?m)^\s*p\.\s*\d+\s*$", "", text)
    text = re.sub(r"(?m)^\s*Página\s*\d+\s*de\s*\d+\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_header_footer(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if _is_header_footer(stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _is_header_footer(line: str) -> bool:
    if not line:
        return False
    patterns = [
        r"^DOC\s*\d+",
        r"^Fls\.\s*\d+",
        r"^Folha\s*\d+",
    ]
    return any(re.match(p, line, re.IGNORECASE) for p in patterns)
