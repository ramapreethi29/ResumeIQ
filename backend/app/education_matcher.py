
import re


# ==================================================
# 1. DEGREE EXTRACTION PATTERNS
# ==================================================

DEGREE_PATTERNS = [
    # Bachelor's degrees
    r"\bBachelor(?:'s)?\s+of\s+Technology\b",
    r"\bBachelor(?:'s)?\s+of\s+Engineering\b",
    r"\bBachelor(?:'s)?\s+of\s+Science\b",
    r"\bBachelor(?:'s)?\s+of\s+Computer Applications\b",

    # Master's degrees
    r"\bMaster(?:'s)?\s+of\s+Technology\b",
    r"\bMaster(?:'s)?\s+of\s+Engineering\b",
    r"\bMaster(?:'s)?\s+of\s+Science\b",
    r"\bMaster(?:'s)?\s+of\s+Computer Applications\b",

    # PhD
    r"\bDoctor\s+of\s+Philosophy\b",

    # Abbreviations
    r"\bB\.?\s*Tech\b",
    r"\bB\.?\s*E\b",
    r"\bB\.?\s*Sc\b",
    r"\bB\.?\s*CA\b",

    r"\bM\.?\s*Tech\b",
    r"\bM\.?\s*E\b",
    r"\bM\.?\s*Sc\b",
    r"\bM\.?\s*CA\b",

    r"\bMBA\b",
    r"\bPh\.?\s*D\b",
]


# ==================================================
# 2. BRANCH EXTRACTION PATTERNS
# ==================================================

BRANCH_PATTERNS = [
    r"computer science and engineering",
    r"computer science",
    r"information technology",
    r"electronics and communication engineering",
    r"electrical and electronics engineering",
    r"mechanical engineering",
    r"civil engineering",
    r"artificial intelligence and machine learning",
    r"artificial intelligence",
    r"machine learning",
    r"data science",
    r"electronics and instrumentation engineering",
    r"computer applications",
    r"finance",
    r"business administration",
    r"statistics",
r"information systems",
r"related field",
r"related discipline"
]


# ==================================================
# 3. NORMALIZE DEGREE
# ==================================================

def normalize_degree(degree):

    if not degree:
        return None

    text = degree.lower().strip()
    text = re.sub(r"[.\s]", "", text)

    degree_mapping = {
        # Bachelor's
        "btech": "B.Tech",
        "bacheloroftechnology": "B.Tech",
        "bachelorsoftechnology": "B.Tech",

        "be": "B.E.",
        "bachelorofengineering": "B.E.",
        "bachelorsofengineering": "B.E.",

        "bsc": "B.Sc",
        "bachelorofscience": "B.Sc",
        "bachelorsofscience": "B.Sc",

        "bca": "BCA",
        "bachelorofcomputerapplications": "BCA",

        # Master's
        "mtech": "M.Tech",
        "masteroftechnology": "M.Tech",

        "me": "M.E.",
        "masterofengineering": "M.E.",

        "msc": "M.Sc",
        "masterofscience": "M.Sc",

        "mca": "MCA",
        "masterofcomputerapplications": "MCA",

        "mba": "MBA",

        # PhD
        "phd": "Ph.D",
        "doctorofphilosophy": "Ph.D"
    }

    return degree_mapping.get(text, degree.strip())


# ==================================================
# 4. EXTRACT EDUCATION DETAILS
# ==================================================
def extract_education_details(education_text: str) -> dict:

    if not education_text:
        return {
            "degree": None,
            "branch": None,
            "graduation_year": None
        }

    text = re.sub(r"\s+", " ", education_text).strip()

    degree_match = None

    for pattern in DEGREE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            degree_match = match.group(0)
            break

    degree = normalize_degree(degree_match)

    branch = None

    for pattern in BRANCH_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            branch = match.group(0)
            break

    year_range = re.search(
        r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?\s*((?:19|20)\d{2})\b",
        text,
        re.IGNORECASE
    )

    if year_range:
        graduation_year = {
            "start_year": year_range.group(1),
            "end_year": year_range.group(2)
        }
    else:
        year_match = re.search(r"\b(?:19|20)\d{2}\b", text)
        graduation_year = year_match.group(0) if year_match else None

    return {
        "degree": degree,
        "branch": branch,
        "graduation_year": graduation_year
    }