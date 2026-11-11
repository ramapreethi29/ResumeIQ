
import re
import unicodedata



def normalize_skill(skill: str) -> str:
    if not skill:
        return ""

    skill = unicodedata.normalize("NFKC", skill)
    skill = re.sub(r"\s+", " ", skill.strip())

    skill = skill.casefold()

    # Remove generic descriptive suffixes.
    skill = re.sub(r"\s+programming$", "", skill)

    return skill



def normalize_skill_list(skills: list[str]) -> list[str]:
    normalized = []
    seen = set()

    for skill in skills:
        value = normalize_skill(skill)

        if value and value not in seen:
            normalized.append(value)
            seen.add(value)

    return normalized


def normalize_jd_skill(skill: str) -> str:
    if not skill:
        return ""

    skill = unicodedata.normalize("NFKC", skill)
    skill = re.sub(r"\s+", " ", skill.strip())

    # Remove generic descriptive prefixes.
    prefixes = [
        r"strong\s+knowledge\s+of",
        r"hands-on\s+experience\s+with",
        r"working\s+knowledge\s+of",
        r"experience\s+with",
        r"experience\s+in",
        r"familiarity\s+with",
        r"knowledge\s+of",
        r"understanding\s+of",
        r"proficiency\s+in",
        r"proficient\s+in",
        r"expertise\s+in",
    ]

    for prefix in prefixes:
        skill = re.sub(
            rf"^{prefix}\s+",
            "",
            skill,
            flags=re.IGNORECASE
        )

    return normalize_skill(skill)


def normalize_jd_skill_list(skills: list[str]) -> list[str]:
    normalized = []
    seen = set()

    for skill in skills:
        value = normalize_jd_skill(skill)

        if value and value not in seen:
            normalized.append(value)
            seen.add(value)

    return normalized


def extract_resume_skills(technical_skills_text: str) -> list[str]:

    if not technical_skills_text:
        return []

    skills = []

    for line in technical_skills_text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Remove category labels when present.
        if ":" in line:
            line = line.split(":", 1)[1]

        parts = re.split(r"[,;|]", line)

        skills.extend(
            part.strip()
            for part in parts
            if part.strip()
        )

    return normalize_skill_list(skills)
