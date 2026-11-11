
import re


# Evidence source priority: most relevant sources first.
SOURCE_PRIORITY = [
    "technical_skills",
    "work_experience",
    "projects",
    "professional_summary",
    "certifications",
    "education",
    "achievements",
    "other",
    "normalized_skills"
]


def normalize(text: str) -> str:
    """Normalize text for case-insensitive matching."""

    text = text.casefold().strip()
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def clean_requirement(requirement: str) -> str:
    """Remove introductory phrases without splitting their internal AND."""

    prefixes = [
        r"developing and maintaining",
        r"experience working with",
        r"experience developing",
        r"hands-on experience with",
        r"hands-on experience in",
        r"experience with",
        r"experience in",
        r"working knowledge of",
        r"strong knowledge of",
        r"knowledge of",
        r"understanding of",
        r"familiarity with",
        r"proficiency in",
        r"proficient in",
        r"expertise in"
    ]

    requirement = requirement.strip()

    for prefix in prefixes:
        requirement = re.sub(
            rf"^{prefix}\s+",
            "",
            requirement,
            flags=re.IGNORECASE
        )

    return requirement.strip()


def clean_skill(skill: str) -> str:
    """Remove generic trailing category words."""

    skill = skill.strip()

    suffixes = [
        r"\s+databases?$",
        r"\s+cloud platforms?$",
        r"\s+methodologies$"
    ]

    for suffix in suffixes:
        skill = re.sub(
            suffix,
            "",
            skill,
            flags=re.IGNORECASE
        )

    return skill.strip()


def split_requirements(requirement: str) -> list[list[str]]:
    """
    OR separates alternatives.
    AND separates components within an alternative.
    """

    requirement = clean_requirement(requirement)

    alternatives = re.split(
        r"\s+or\s+",
        requirement,
        flags=re.IGNORECASE
    )

    components = []

    for alternative in alternatives:

        parts = re.split(
            r"\s+and\s+",
            alternative,
            flags=re.IGNORECASE
        )

        components.append([
            clean_skill(part)
            for part in parts
            if clean_skill(part)
        ])

    return components


def collect_resume_evidence(resume_data: dict) -> list[dict]:
    """
    Collect evidence from all relevant resume sections.

    Supports:
    - sections dictionary
    - normalized_skills list
    - education dictionary
    - experience dictionary
    """

    evidence = []

    if not isinstance(resume_data, dict):
        return evidence

    sections = resume_data.get("sections", {})

    if not isinstance(sections, dict):
        sections = {}

    def add_evidence(source: str, value):

        if isinstance(value, str):

            if value.strip():
                evidence.append({
                    "source": source,
                    "text": value.strip()
                })

        elif isinstance(value, list):

            for item in value:
                add_evidence(source, item)

        elif isinstance(value, dict):

            for key, item in value.items():
                add_evidence(f"{source}.{key}", item)

    # First collect normal resume sections.
    for source in SOURCE_PRIORITY:

        if source == "normalized_skills":
            continue

        value = sections.get(source)

        if value is None:
            # Some parsers store education outside sections.
            value = resume_data.get(source)

        if value is not None:
            add_evidence(source, value)

    # Normalized skills are useful as an additional source.
    add_evidence(
        "normalized_skills",
        resume_data.get("normalized_skills", [])
    )

    # Include parsed experience data if available.
    experience = resume_data.get("experience", {})

    if isinstance(experience, dict):

        for category, details in experience.items():

            if isinstance(details, dict):

                add_evidence(
                    f"experience.{category}",
                    details.get("records", [])
                )

    return evidence


def find_skill_evidence(
    skill: str,
    evidence: list[dict]
) -> list[dict]:
    """Find exact phrase evidence using word boundaries."""

    target = normalize(skill)

    if not target:
        return []

    pattern = (
        rf"(?<![a-z0-9+#.]){re.escape(target)}"
        rf"(?![a-z0-9+#.])"
    )

    matches = []

    for item in evidence:

        text = normalize(item.get("text", ""))

        if re.search(pattern, text):

            matches.append({
                "source": item["source"],
                "text": item["text"]
            })

    return matches


def limit_top_sources(matches: list[dict]) -> list[dict]:
    """Return at most three unique evidence sources."""

    unique = []
    seen = set()

    for item in matches:

        source = item["source"]

        if source not in seen:

            seen.add(source)
            unique.append(item)

        if len(unique) == 3:
            break

    return unique


def match_skill_category(
    jd_skills: list[str],
    evidence: list[dict]
) -> dict:

    results = {
        "match": [],
        "unmatch": [],
        "unknown": []
    }

    for requirement in jd_skills:

        alternatives = split_requirements(requirement)

        best_matched = []
        best_missing = []
        best_evidence = []

        # Evaluate every OR alternative.
        for alternative in alternatives:

            matched = []
            missing = []
            alternative_evidence = []

            # Every AND component must be found for a full match.
            for component in alternative:

                matches = find_skill_evidence(
                    component,
                    evidence
                )

                if matches:

                    matched.append(component)
                    alternative_evidence.extend(matches)

                else:

                    missing.append(component)

            # Prefer a complete match.
            if not missing and matched:

                best_matched = matched
                best_missing = []
                best_evidence = alternative_evidence
                break

            # Otherwise retain the alternative with most matches.
            if len(matched) > len(best_matched):

                best_matched = matched
                best_missing = missing
                best_evidence = alternative_evidence

        result = {
            "requirement": requirement,
            "matched_skills": best_matched,
            "missing_skills": best_missing,
            "evidence": limit_top_sources(best_evidence)
        }

        if best_matched and not best_missing:

            result["reason"] = (
                "All components of at least one alternative were found."
            )

            results["match"].append(result)

        elif best_matched:

            result["partial_match"] = True

            result["reason"] = (
                "Some components were found, but others are missing."
            )

            results["unmatch"].append(result)

        elif evidence:

            # No component found: report all components of
            # the first alternative as missing.
            first_alternative = (
                alternatives[0] if alternatives else []
            )

            result["missing_skills"] = first_alternative
            result["not_found"] = True
            result["reason"] = (
                "Requirement not found in any resume section."
            )

            results["unmatch"].append(result)

        else:

            result["reason"] = (
                "Resume information is unavailable."
            )

            results["unknown"].append(result)

    return results


def match_skills(jd_data: dict, resume_data: dict) -> dict:
    """Compare required and preferred JD skills with resume evidence."""

    evidence = collect_resume_evidence(resume_data)

    return {
        "required": match_skill_category(
            jd_data.get("required", {}).get("skills", []),
            evidence
        ),

        "preferred": match_skill_category(
            jd_data.get("preferred", {}).get("skills", []),
            evidence
        )
    }
