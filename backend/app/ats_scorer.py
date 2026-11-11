
import re

from app.requirement_matcher import format_experience_requirement


# ==================================================
# ATS SCORING WEIGHTS
# ==================================================

REQUIRED_WEIGHTS = {
    "skills": 40,
    "others": 5,
    "education": 10,
    "experience": 20,
    "certifications": 10
}

PREFERRED_WEIGHT = 15


# ==================================================
# NORMALIZATION
# ==================================================

def normalize_requirement(value):
    return re.sub(
        r"\s+",
        " ",
        str(value).strip().casefold()
    )


# ==================================================
# GET REQUIREMENTS BY CATEGORY
# ==================================================

def get_category_requirements(category):

    requirements = []

    # Skills
    requirements.extend(category.get("skills", []))

    # Certifications
    requirements.extend(category.get("certifications", []))

    # Other requirements
    requirements.extend(category.get("other_requirements", []))

    # Education
    education = category.get("education", {}) or {}

    degrees = education.get("degree", [])
    branches = education.get("branch", [])

    if degrees:
        requirements.append(" OR ".join(degrees))

    if branches:
        requirements.append(" OR ".join(branches))

    graduation_year = education.get("graduation_year")

    if graduation_year is not None:
        requirements.append(str(graduation_year))

    # Experience
    experience = category.get("experience", {}) or {}

    for experience_type in ("professional", "internship"):

        experience_range = experience.get(experience_type)

        if experience_range:
            label = format_experience_requirement(
                experience_type,
                experience_range
            )

            if label:
                requirements.append(label)

    requirements.extend(
        experience.get("alternative_paths", [])
    )

    return requirements


# ==================================================
# REQUIREMENT STATUS
# ==================================================

def get_status(requirement, matching, missing):

    key = normalize_requirement(requirement)

    matched_items = {
        normalize_requirement(item)
        for item in matching
    }

    missing_items = {
        normalize_requirement(item)
        for item in missing
    }

    if key in matched_items:
        return "matched"

    if key in missing_items:
        return "missing"

    return "not_assessed"


# ==================================================
# CATEGORY SCORE
# ==================================================

def calculate_category_score(
    requirements,
    matching,
    missing,
    weight,
    unknown_requirements=None
):

    unknown_requirements = unknown_requirements or set()

    matched_count = 0
    assessed_count = 0
    missing_count = 0

    for requirement in requirements:

        if normalize_requirement(requirement) in unknown_requirements:
            continue

        status = get_status(
            requirement,
            matching,
            missing
        )

        if status == "matched":
            matched_count += 1
            assessed_count += 1

        elif status == "missing":
            missing_count += 1
            assessed_count += 1

    if assessed_count == 0:

        return {
            "score": None,
            "weight": weight,
            "matched": 0,
            "missing": 0,
            "total": 0,
            "status": "not_assessable"
        }

    score = round(
        (matched_count / assessed_count) * weight,
        2
    )

    return {
        "score": score,
        "weight": weight,
        "matched": matched_count,
        "missing": missing_count,
        "total": assessed_count,
        "status": "assessed"
    }


# ==================================================
# MAIN ATS SCORING FUNCTION
# ==================================================

def calculate_ats_score(
    jd_requirements,
    matching_requirements,
    missing_requirements,
    experience_analysis=None
):

    required_jd = jd_requirements.get("required", {})
    preferred_jd = jd_requirements.get("preferred", {})

    matching = matching_requirements
    missing = missing_requirements

    experience_analysis = experience_analysis or {}

    # --------------------------------------------------
    # Identify experience requirements that cannot
    # currently be assessed from the resume.
    # --------------------------------------------------

    unknown_experience = set()

    for experience_type in ("professional", "internship"):

        experience_data = experience_analysis.get(
            experience_type, {}
        ) or {}

        if experience_data.get("duration_months") is None:

            experience_range = (
                required_jd.get("experience", {}).get(
                    experience_type
                )
            )

            if experience_range:

                label = format_experience_requirement(
                    experience_type,
                    experience_range
                )

                if label:
                    unknown_experience.add(
                        normalize_requirement(label)
                    )

    
    # --------------------------------------------------
    # REQUIRED CATEGORY SCORES
    # --------------------------------------------------

    category_scores = {}

    total_earned = 0
    total_available_weight = 0

    for category, weight in REQUIRED_WEIGHTS.items():

        if category == "skills":
            requirements = required_jd.get("skills", [])

        elif category == "certifications":
            requirements = required_jd.get("certifications", [])

        elif category == "others":
            requirements = required_jd.get("other_requirements", [])

        elif category in ("education", "experience"):
            requirements = get_category_requirements({
                category: required_jd.get(category, {})
            })

        category_unknown = (
            unknown_experience
            if category == "experience"
            else set()
        )

        result = calculate_category_score(
            requirements,
            matching.get(category, []),
            missing.get(category, []),
            weight,
            category_unknown
        )

        category_scores[category] = result

        if result["status"] == "assessed":
            total_earned += result["score"]
            total_available_weight += weight

    # --------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------

    overall_score = None

    if total_available_weight > 0:

        overall_score = round(
            (total_earned / total_available_weight) * 100
        )

    if overall_score is None:
        rating = "Not enough information"

    elif overall_score >= 80:
        rating = "Strong Match"

    elif overall_score >= 60:
        rating = "Moderate Match"

    elif overall_score >= 40:
        rating = "Low Match"

    else:
        rating = "Weak Match"

    return {
        "overall_score": overall_score,
        "rating": rating,
        "category_scores": category_scores,
        "available_weight": total_available_weight,
        "maximum_weight": 100
    }
