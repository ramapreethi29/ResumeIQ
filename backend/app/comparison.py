import re

from app.matchers.experience_matcher import match_experience
from app.matchers.skill_matcher import match_skills


DIMENSIONS = (
    "skills",
    "experience",
    "education",
    "certifications",
    "other",
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "for", "from", "in",
    "is", "of", "on", "or", "the", "to", "with", "must", "should",
    "able", "ability", "including", "using", "work", "working",
}


def _item(name, status, reason, evidence=None):
    points = {"match": 1.0, "partial": 0.5, "unmatch": 0.0, "unknown": 0.0}
    return {
        "item": name,
        "status": status,
        "points": points[status],
        "reason": reason,
        "evidence": evidence or [],
    }


def _ratio(items):
    if not items:
        return None
    return round(sum(item["points"] for item in items) / len(items), 4)


def _resume_blob(resume_data):
    parts = []
    sections = resume_data.get("sections") or {}
    if isinstance(sections, dict):
        parts.extend(str(value) for value in sections.values() if value)
    parts.extend(resume_data.get("normalized_skills") or [])
    education = resume_data.get("education") or {}
    if isinstance(education, dict):
        parts.extend(str(value) for value in education.values() if value)
    return "\n".join(parts)


def _tokens(text):
    words = re.findall(r"[a-z0-9+#]+", (text or "").casefold())
    return [word for word in words if word not in STOPWORDS and len(word) > 2]


def _contains_phrase(phrase, text):
    phrase_tokens = _tokens(phrase)
    if not phrase_tokens:
        return False
    haystack = set(_tokens(text))
    if len(phrase_tokens) == 1:
        return phrase_tokens[0] in haystack
    found = sum(1 for token in phrase_tokens if token in haystack)
    return found / len(phrase_tokens) >= 0.7


def _skill_items(category_result):
    items = []
    for row in category_result.get("match", []):
        items.append(_item(
            row.get("requirement", ""),
            "match",
            row.get("reason", "Skill found in the resume."),
            row.get("evidence"),
        ))
    for row in category_result.get("unmatch", []):
        status = "partial" if row.get("partial_match") else "unmatch"
        items.append(_item(
            row.get("requirement", ""),
            status,
            row.get("reason", "Skill was not fully found."),
            row.get("evidence"),
        ))
    for row in category_result.get("unknown", []):
        items.append(_item(
            row.get("requirement", ""),
            "unknown",
            row.get("reason", "Resume evidence is unavailable."),
        ))
    return items


def _resume_months(resume_data):
    experience = resume_data.get("experience") or {}
    professional = experience.get("professional") or {}
    internship = experience.get("internship") or {}
    professional_months = (
        professional.get("duration_months")
        if isinstance(professional, dict)
        else experience.get("professional_months")
    )
    internship_months = (
        internship.get("duration_months")
        if isinstance(internship, dict)
        else experience.get("internship_months")
    )
    return {
        "professional_months": professional_months,
        "internship_months": internship_months,
    }


def _experience_items(category_result, requirement, resume_text):
    items = []
    labels = {
        "professional": "Professional experience",
        "internship": "Internship experience",
    }
    for kind, label in labels.items():
        requirement_range = (requirement or {}).get(kind)
        if not requirement_range:
            continue
        bucket = category_result.get(kind, {})
        placed = False
        for status in ("match", "unmatch", "unknown"):
            for row in bucket.get(status, []):
                items.append(_item(
                    label,
                    status,
                    row.get("reason", ""),
                    [f"{row.get('resume_experience_months')} months on resume"],
                ))
                placed = True
        if not placed:
            items.append(_item(label, "unknown", "Experience could not be compared."))

    alternatives = (requirement or {}).get("alternative_paths") or []
    professional_failed = any(
        item["item"] == "Professional experience" and item["status"] != "match"
        for item in items
    )
    if professional_failed and alternatives:
        matched_path = next(
            (path for path in alternatives if _contains_phrase(path, resume_text)),
            None,
        )
        if matched_path:
            for item in items:
                if item["item"] == "Professional experience":
                    item["status"] = "match"
                    item["points"] = 1.0
                    item["reason"] = (
                        "Professional duration was not met, but an explicit "
                        f"alternative path was found: {matched_path}."
                    )
                    item["evidence"] = [matched_path]
    return items


def _degree_level(value):
    text = re.sub(r"[^a-z0-9]", "", (value or "").casefold())
    if not text:
        return 0
    if any(token in text for token in ("phd", "doctorofphilosophy")):
        return 3
    if any(token in text for token in (
        "master", "mtech", "me", "msc", "mca", "mba", "ms"
    )):
        return 2
    if any(token in text for token in (
        "bachelor", "btech", "be", "bsc", "bca", "bs"
    )):
        return 1
    return 0


def _year_values(value):
    if value is None:
        return set()
    if isinstance(value, dict):
        years = []
        for key in ("end_year", "start_year", "graduation_year"):
            if value.get(key):
                years.append(str(value[key]))
        return {int(year) for year in years if str(year).isdigit()}
    found = re.findall(r"(?:19|20)\d{2}", str(value))
    return {int(year) for year in found}


def _education_items(requirement, resume_education):
    requirement = requirement or {}
    resume_education = resume_education or {}
    degrees = requirement.get("degree") or []
    branches = requirement.get("branch") or []
    graduation_year = requirement.get("graduation_year")
    if not degrees and not branches and graduation_year is None:
        return []

    checks = []
    resume_degree = resume_education.get("degree")
    if degrees:
        resume_level = _degree_level(resume_degree)
        accepted = max((_degree_level(degree) for degree in degrees), default=0)
        if resume_level == 0:
            checks.append(("Degree", "unknown", "Resume degree was not extracted."))
        elif resume_level >= accepted and accepted > 0:
            checks.append((
                "Degree",
                "match",
                f"Resume degree '{resume_degree}' meets {', '.join(degrees)}.",
            ))
        else:
            checks.append((
                "Degree",
                "unmatch",
                f"Resume degree '{resume_degree}' does not meet {', '.join(degrees)}.",
            ))

    resume_branch = (resume_education.get("branch") or "").casefold()
    specific_branches = [
        branch for branch in branches
        if "related" not in branch.casefold()
    ]
    if specific_branches:
        if not resume_branch:
            checks.append(("Field of study", "unknown", "Resume branch was not extracted."))
        elif any(branch.casefold() in resume_branch or resume_branch in branch.casefold()
                  for branch in specific_branches):
            checks.append((
                "Field of study",
                "match",
                f"Resume field '{resume_education.get('branch')}' matches the job.",
            ))
        else:
            checks.append((
                "Field of study",
                "unmatch",
                f"Resume field '{resume_education.get('branch')}' does not match "
                f"{', '.join(specific_branches)}.",
            ))

    if graduation_year is not None:
        resume_years = _year_values(resume_education.get("graduation_year"))
        if not resume_years:
            checks.append(("Graduation year", "unknown", "Resume graduation year was not extracted."))
        elif int(graduation_year) in resume_years:
            checks.append(("Graduation year", "match", "Graduation year matches."))
        else:
            checks.append((
                "Graduation year",
                "unmatch",
                f"Resume year {sorted(resume_years)} does not match {graduation_year}.",
            ))

    return [_item(name, status, reason) for name, status, reason in checks]


def _list_items(requirements, resume_text, found_reason, missing_reason):
    items = []
    for requirement in requirements or []:
        if _contains_phrase(requirement, resume_text):
            items.append(_item(requirement, "match", found_reason, [requirement]))
        elif not resume_text.strip():
            items.append(_item(requirement, "unknown", "Resume text is unavailable."))
        else:
            items.append(_item(requirement, "unmatch", missing_reason))
    return items


def _empty_category():
    return {
        "skills": [],
        "experience": {
            "professional": None,
            "internship": None,
            "alternative_paths": [],
        },
        "education": {"degree": [], "branch": [], "graduation_year": None},
        "certifications": [],
        "other_requirements": [],
    }


def compare_resume_to_jd(resume_data: dict, jd_data: dict) -> dict:
    """Compare extracted resume facts with required and preferred JD groups."""
    resume_data = resume_data or {}
    jd_data = jd_data or {}
    resume_text = _resume_blob(resume_data)
    skill_result = match_skills(jd_data, resume_data)
    experience_result = match_experience(
        jd_data,
        {"experience": _resume_months(resume_data)},
    )

    comparison = {}
    for side in ("required", "preferred"):
        category = jd_data.get(side) or _empty_category()
        skills = _skill_items(skill_result.get(side, {}))
        experience = _experience_items(
            experience_result.get(side, {}),
            category.get("experience"),
            resume_text,
        )
        education = _education_items(
            category.get("education"),
            resume_data.get("education"),
        )
        certifications = _list_items(
            category.get("certifications"),
            resume_text,
            "Certification text was found in the resume.",
            "Certification was not found in the resume.",
        )
        other = _list_items(
            category.get("other_requirements"),
            resume_text,
            "Requirement wording was found in the resume.",
            "Requirement was not found in the resume.",
        )
        groups = {
            "skills": skills,
            "experience": experience,
            "education": education,
            "certifications": certifications,
            "other": other,
        }
        comparison[side] = {
            name: {"items": items, "score": _ratio(items)}
            for name, items in groups.items()
        }
    return comparison
