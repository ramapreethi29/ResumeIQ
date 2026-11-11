
import re
import unicodedata
from app.skill_normalizer import normalize_jd_skill
try:
    from .semantic_matcher import semantic_match
except ImportError:
    from app.semantic_matcher import semantic_match


# ==================================================
# 1. TEXT NORMALIZATION
# ==================================================

STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on",
    "to", "for", "with", "using", "by", "as", "at",
    "is", "are", "be", "ability", "experience",
    "knowledge", "understanding", "familiarity",
    "proficiency", "proficient", "strong", "good",
    "skills", "skill"
}


def normalize_text(text):

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", str(text))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9+#/.-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text):

    normalized = normalize_text(text)

    return re.findall(
        r"c\+\+|c#|ci/cd|[a-z0-9]+",
        normalized
    )


def normalize_token(token):

    if len(token) <= 3:
        return token

    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"

    if token.endswith("ing") and len(token) > 5:
        return token[:-3]

    if token.endswith("ed") and len(token) > 4:
        return token[:-2]

    if token.endswith("s") and len(token) > 4:
        return token[:-1]

    return token


def get_meaningful_tokens(text):

    return {
        normalize_token(token)
        for token in tokenize(text)
        if token not in STOP_WORDS
    }


# ==================================================
# 2. BUILD RESUME SECTIONS
# ==================================================

def build_resume_sections(resume_data):

    sections = resume_data.get("sections", {})

    # Skills: normalized skills ONLY
    skill_evidence = [
        str(skill)
        for skill in resume_data.get("normalized_skills", [])
        if skill
    ]

    # Certifications: certification section ONLY
    certification_text = sections.get("certifications", "")

    certification_evidence = [
        certification_text
    ] if certification_text else []

    # Education: structured data + education text
    education = resume_data.get("education", {})

    education_evidence = {
        "degree": education.get("degree", ""),
        "branch": education.get("branch", ""),
        "graduation_year": education.get("graduation_year", {}),
        "education_text": sections.get("education", "")
    }

    # Experience: structured data + work experience text
    experience_evidence = {
        "experience_data": resume_data.get("experience", {}),
        "work_experience_text": sections.get(
            "work_experience", ""
        )
    }

    # Others: ONLY four selected resume sources
    other_evidence = []

    # 1. Normalized skills
    other_evidence.extend(skill_evidence)

    # 2. Professional summary
    # 3. Projects
    # 4. Achievements
    for section_name in (
        "professional_summary",
        "projects",
        "achievements"
    ):

        section_text = sections.get(section_name, "")

        if section_text:
            other_evidence.append(str(section_text))

    return {
        "skills": skill_evidence,
        "certifications": certification_evidence,
        "education": education_evidence,
        "experience": experience_evidence,
        "others": other_evidence
    }


# ==================================================
# 3. PHRASE MATCHING
# ==================================================

def contains_phrase(requirement, evidence):

    requirement_tokens = tokenize(requirement)
    evidence_tokens = tokenize(evidence)

    if not requirement_tokens:
        return False

    size = len(requirement_tokens)

    normalized_requirement = [
        normalize_token(token)
        for token in requirement_tokens
    ]

    for index in range(len(evidence_tokens) - size + 1):

        candidate = evidence_tokens[index:index + size]

        normalized_candidate = [
            normalize_token(token)
            for token in candidate
        ]

        if normalized_candidate == normalized_requirement:
            return True

    return False


def match_phrase(requirement, evidence_sections):

    if isinstance(evidence_sections, str):
        evidence_sections = [evidence_sections]

    for evidence in evidence_sections:

        if not evidence:
            continue

        if contains_phrase(requirement, evidence):
            return True

        requirement_tokens = get_meaningful_tokens(
            requirement
        )

        evidence_tokens = get_meaningful_tokens(
            evidence
        )

        if (
            requirement_tokens
            and requirement_tokens.issubset(evidence_tokens)
        ):
            return True

    return False


# ==================================================
# 4. ALTERNATIVE REQUIREMENTS
# ==================================================

def split_alternatives(requirement):

    return [
        part.strip()
        for part in re.split(
            r"\s+\bor\b\s+",
            requirement,
            flags=re.IGNORECASE
        )
        if part.strip()
    ]


def requirement_matches(requirement, evidence_sections):

    alternatives = split_alternatives(requirement)

    return any(
        match_phrase(alternative, evidence_sections)
        for alternative in alternatives
    )


# ==================================================
# 5. SKILL AND CERTIFICATION MATCHING
# EXACT + BGE + QWEN
# ==================================================

def match_semantic_requirement(requirement, evidence):

    # Normalize JD requirement
    normalized_requirement = normalize_jd_skill(requirement)

    # First: exact matching
    exact_match = requirement_matches(
        normalized_requirement,
        evidence
    )

    if exact_match:
        return True

    # Second: semantic matching with BGE + Qwen
    try:

        return semantic_match(
            normalized_requirement,
            evidence
        )

    except Exception:

        return False


# ==================================================
# 6. EDUCATION COMPARISON
# PYTHON ONLY
# ==================================================

def match_degree(jd_degree, resume_degree):

    jd = normalize_text(jd_degree)
    resume = normalize_text(resume_degree)

    if not jd or not resume:
        return False

    if "bachelor" in jd:

        bachelor_aliases = [
            "b.tech",
            "btech",
            "b tech",
            "bachelor of technology",
            "b.e",
            "be",
            "bachelor of engineering"
        ]

        if any(alias in resume for alias in bachelor_aliases):
            return True

    return contains_phrase(
        jd_degree,
        resume_degree
    )


def match_graduation_year(jd_year, resume_year):

    if jd_year is None:
        return None

    if resume_year is None:
        return False

    jd_years = set(
        re.findall(r"\b(?:19|20)\d{2}\b", str(jd_year))
    )

    resume_years = set(
        re.findall(r"\b(?:19|20)\d{2}\b", str(resume_year))
    )

    if not jd_years:
        return None

    return bool(
        jd_years.intersection(resume_years)
    )


# ==================================================
# 7. EXPERIENCE COMPARISON
# PYTHON ONLY
# ==================================================

def match_experience(jd_range, resume_experience):

    if not isinstance(jd_range, dict):
        return None

    if not isinstance(resume_experience, dict):
        return None

    minimum = jd_range.get("minimum_months")

    candidate_months = resume_experience.get(
        "duration_months"
    )

    if candidate_months is None:
        return None

    if minimum is not None and candidate_months < minimum:
        return False

    # Maximum is not a disqualifying limit.
    return True


def format_months(months, plus=False):

    suffix = "+" if plus else ""

    if months % 12 == 0:
        return f"{months // 12}{suffix} years"

    return f"{months}{suffix} months"


def format_experience_requirement(category, value):

    if not isinstance(value, dict):
        return None

    minimum = value.get("minimum_months")
    maximum = value.get("maximum_months")

    if minimum is None and maximum is None:
        return None

    if minimum is not None and maximum is not None:

        return (
            f"{category.title()} experience: "
            f"{format_months(minimum)} to "
            f"{format_months(maximum)}"
        )

    if minimum is not None:

        return (
            f"{category.title()} experience: "
            f"{format_months(minimum, plus=True)}"
        )

    return (
        f"{category.title()} experience: "
        f"up to {format_months(maximum)}"
    )


# ==================================================
# 8. OUTPUT STRUCTURE
# ==================================================

def create_result_structure():

    return {
        "skills": [],
        "certifications": [],
        "experience": [],
        "education": [],
        "others": []
    }


def add_result(
    requirement,
    matched,
    matching,
    missing,
    category
):

    if matched:
        matching[category].append(requirement)

    else:
        missing[category].append(requirement)


# ==================================================
# 9. JD-FIRST COMPARISON
# ==================================================

def compare_requirements(jd_requirements, resume_data):

    matching_requirements = create_result_structure()
    missing_requirements = create_result_structure()

    resume_sections = build_resume_sections(resume_data)

    resume_education = resume_data.get("education", {})
    resume_experience = resume_data.get("experience", {})

    # Prevent duplicate requirements across required and preferred
    processed_requirements = set()

    def add_unique_result(requirement, matched, category):

        normalized = re.sub(
            r"\s+",
            " ",
            str(requirement).strip().lower()
        )

        key = (category, normalized)

        if key in processed_requirements:
            return

        processed_requirements.add(key)

        add_result(
            requirement,
            matched,
            matching_requirements,
            missing_requirements,
            category
        )

    # --------------------------------------------------
    # A. SKILLS
    # --------------------------------------------------

    for jd_level in ("required", "preferred"):

        jd_category = jd_requirements.get(jd_level, {})

        for skill in jd_category.get("skills", []):

            # Handle equivalent REST API skill wording
            normalized_skill = re.sub(
                r"\s+",
                " ",
                skill.lower().strip()
            )

            resume_skills = resume_sections["skills"]

            if normalized_skill == "rest api development":

                matched = any(
                    re.sub(
                        r"\s+",
                        " ",
                        candidate.lower().strip()
                    ) in (
                        "rest api",
                        "rest apis",
                        "restful api",
                        "restful apis",
                        "rest api development",
                        "restful api development"
                    )
                    for candidate in resume_skills
                )

            else:

                matched = match_semantic_requirement(
                    skill,
                    resume_skills
                )

            add_unique_result(
                skill,
                matched,
                "skills"
            )

        # --------------------------------------------------
        # B. CERTIFICATIONS
        # --------------------------------------------------

        for certification in jd_category.get(
            "certifications", []
        ):

            matched = match_semantic_requirement(
                certification,
                resume_sections["certifications"]
            )

            add_unique_result(
                certification,
                matched,
                "certifications"
            )

        # --------------------------------------------------
        # C. EDUCATION
        # --------------------------------------------------

        jd_education = jd_category.get(
            "education", {}
        ) or {}

        # Degree

        degrees = jd_education.get("degree", [])

        if degrees:

            degree_label = " OR ".join(degrees)

            degree_match = any(
                match_degree(
                    degree,
                    resume_education.get("degree", "")
                )
                for degree in degrees
            )

            add_unique_result(
                degree_label,
                degree_match,
                "education"
            )

        # Branch

        branches = jd_education.get("branch", [])

        if branches:

            branch_label = " OR ".join(branches)

            branch_match = any(
                requirement_matches(
                    branch,
                    [
                        resume_education.get("branch", ""),
                        resume_sections["education"]["education_text"]
                    ]
                )
                for branch in branches
            )

            add_unique_result(
                branch_label,
                branch_match,
                "education"
            )

        # Graduation year

        graduation_year = jd_education.get(
            "graduation_year"
        )

        if graduation_year is not None:

            year_match = match_graduation_year(
                graduation_year,
                resume_education.get("graduation_year")
            )

            add_unique_result(
                str(graduation_year),
                year_match is True,
                "education"
            )

        # --------------------------------------------------
        # D. EXPERIENCE
        # --------------------------------------------------

        jd_experience = jd_category.get(
            "experience", {}
        ) or {}

        for experience_type in (
            "professional",
            "internship"
        ):

            jd_range = jd_experience.get(experience_type)

            if not jd_range:
                continue

            label = format_experience_requirement(
                experience_type,
                jd_range
            )

            if not label:
                continue

            result = match_experience(
                jd_range,
                resume_experience.get(experience_type, {})
            )

            add_unique_result(
                label,
                result is True,
                "experience"
            )

        # Alternative experience paths

        for alternative in jd_experience.get(
            "alternative_paths", []
        ):

            matched = requirement_matches(
                alternative,
                resume_sections["experience"]["work_experience_text"]
            )

            add_unique_result(
                alternative,
                matched,
                "experience"
            )

        
         # --------------------------------------------------
        # E. OTHER REQUIREMENTS
        # Required + Preferred
        # --------------------------------------------------

        for requirement in jd_category.get(
            "other_requirements", []
        ):

            matched = match_semantic_requirement(
                requirement,
                resume_sections["others"]
            )

            add_unique_result(
                requirement,
                matched,
                "others"
            )
       

    return {
        "matching_requirements": matching_requirements,
        "missing_requirements": missing_requirements
    }

