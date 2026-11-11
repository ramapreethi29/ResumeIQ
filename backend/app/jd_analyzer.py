import re
import time
import json
import hashlib

from pathlib import Path

import re
import time

from langchain_ollama import ChatOllama

from app.jd_schemas import JDExtraction

from app.skill_normalizer import (
    normalize_jd_skill_list,
    normalize_skill,
    normalize_jd_skill
)

from app.education_matcher import (
    DEGREE_PATTERNS,
    BRANCH_PATTERNS,
    normalize_degree
)

from app.jd_experience_extractor import extract_jd_experience

# ==================================================
# JD EXTRACTION CACHE
# ==================================================

JD_CACHE_DIR = (
    Path(__file__).resolve().parent.parent
    / "cache"
    / "jd_extractions"
)

JD_CACHE_VERSION = "v12"
JD_MODEL_NAME = "qwen2.5:7b"


def get_jd_cache_path(job_description):

    cache_input = (
        JD_CACHE_VERSION
        + JD_MODEL_NAME
        + job_description.strip().casefold()
    )
    print("JD VERSION:", JD_CACHE_VERSION)
    print("JD MODEL:", JD_MODEL_NAME)
    print("JD INPUT LENGTH:", len(job_description.strip()))
    print("JD INPUT HASH TEXT:", repr(job_description.strip().casefold()))
    jd_hash = hashlib.sha256(
        cache_input.encode("utf-8")
    ).hexdigest()

    cache_path = JD_CACHE_DIR / f"{jd_hash}.json"

    print("JD CACHE FILE:", cache_path)

    return cache_path

def load_jd_cache(cache_path):

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return None


def save_jd_cache(cache_path, result):

    JD_CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False
        )
# ==================================================
# 1. BASIC CLEANING
# ==================================================

def clean_list(values):

    if not values:
        return []

    if isinstance(values, str):
        values = [values]

    result = []
    seen = set()

    for value in values:

        if not isinstance(value, str):
            continue

        value = re.sub(r"\s+", " ", value.strip())
        value = value.rstrip(".;")

        key = re.sub(
            r"[^a-z0-9+#]",
            "",
            value.casefold()
        )

        if value and key and key not in seen:
            result.append(value)
            seen.add(key)

    return result


def normalize_text(value):

    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip()
    )

# ==================================================
# 1A. SOURCE SECTION VALIDATION
# ==================================================

def normalize_source_text(text):

    if not text:
        return ""

    return normalize_text(text).casefold()


def filter_items_by_source(items, source_text):
    """
    Keep extracted items only when they appear
    in the corresponding original JD section.

    If the original section is unavailable,
    preserve the extracted items.
    """

    source = normalize_source_text(source_text)

    if not source:
        return items

    filtered = []

    for item in items:

        normalized_item = normalize_source_text(item)

        if normalized_item and normalized_item in source:
            filtered.append(item)

    return filtered
# ==================================================
# 2. SKILL NORMALIZATION
# ==================================================
def normalize_skill_names(skills):

    normalized = []
    seen = set()

    for skill in clean_list(skills):

        # Split independent skills connected by AND.
        # Preserve OR alternatives together.

        parts = re.split(
            r"\s+\band\b\s+",
            skill,
            flags=re.IGNORECASE
        )

        for part in parts:

            item = normalize_jd_skill(part)

            if item and item not in seen:
                normalized.append(item)
                seen.add(item)

    return normalized
# ==================================================
# 3. EDUCATION NORMALIZATION
# ==================================================

def normalize_jd_degrees(degrees):

    normalized = []

    for degree in degrees or []:

        if not isinstance(degree, str):
            continue

        degree = normalize_text(degree)

        if not degree:
            continue

        lower = degree.casefold()

        if "bachelor" in lower:

            normalized.append("bachelor")

        elif "master" in lower:

            normalized.append("master")

        else:

            normalized.append(
                (
                    normalize_degree(degree)
                    or degree
                ).casefold()
            )

    return clean_list(normalized)


def normalize_education(education):

    education = education or {}

    graduation_year = education.get("graduation_year")

    if isinstance(graduation_year, str):

        if graduation_year.isdigit():
            graduation_year = int(graduation_year)

        else:
            graduation_year = None

    if not isinstance(graduation_year, int):
        graduation_year = None

    return {
        "degree": normalize_jd_degrees(
            education.get("degree", [])
        ),

        "branch": clean_list(
            education.get("branch", [])
        ),

        "graduation_year": graduation_year
    }


# ==================================================
# 3A. DETERMINISTIC JD EDUCATION EXTRACTION
# ==================================================

def extract_jd_education(job_description):

    result = {
        "required": {
            "degree": [],
            "branch": []
        },

        "preferred": {
            "degree": [],
            "branch": []
        }
    }

    current_category = "required"

    degree_patterns = list(DEGREE_PATTERNS) + [
        r"\bBachelor(?:'s)?\s+degree\b",
        r"\bMaster(?:'s)?\s+degree\b",
        r"\bundergraduate\s+degree\b",
        r"\bgraduate\s+degree\b"
    ]

    branch_patterns = list(BRANCH_PATTERNS) + [
        r"\bstatistics\b"
    ]

    for line in job_description.splitlines():

        line = line.strip()

        if not line:
            continue

        lower = line.casefold()

        if re.search(
            r"\b(preferred|desired|nice to have|good to have|"
            r"bonus qualifications|desirable)\b",
            lower
        ):

            current_category = "preferred"

        elif re.search(
            r"\b(required|minimum qualifications|mandatory|"
            r"basic qualifications)\b",
            lower
        ):

            current_category = "required"

        category = current_category

        # ------------------------------------------
        # Extract degrees
        # ------------------------------------------

        for pattern in degree_patterns:

            for match in re.finditer(
                pattern,
                line,
                re.IGNORECASE
            ):

                degree = normalize_degree(match.group(0))

                if degree:

                    result[category]["degree"].append(degree)

        # ------------------------------------------
        # Extract branches
        # ------------------------------------------

        branch_matches = []

        for pattern in branch_patterns:

            for match in re.finditer(
                pattern,
                line,
                re.IGNORECASE
            ):

                branch_matches.append(match)

        branch_matches.sort(
            key=lambda match: (
                match.start(),
                -(match.end() - match.start())
            )
        )

        accepted_spans = []

        for match in branch_matches:

            start, end = match.span()

            if any(
                start < previous_end
                and end > previous_start
                for previous_start, previous_end
                in accepted_spans
            ):

                continue

            branch = match.group(0).strip()

            # Generic phrases are not specific branches.

            if re.fullmatch(
                r"related\s+(?:field|discipline)",
                branch,
                re.IGNORECASE
            ):

                continue

            if branch:

                result[category]["branch"].append(branch)

                accepted_spans.append((start, end))

    # ----------------------------------------------
    # Normalize education results
    # ----------------------------------------------

    for category in ("required", "preferred"):

        result[category]["degree"] = normalize_jd_degrees(
            result[category]["degree"]
        )

        result[category]["branch"] = clean_list(
            result[category]["branch"]
        )

    return result


# ==================================================
# 4. EXPERIENCE NORMALIZATION
# ==================================================

def normalize_experience(experience):

    """
    Experience comes ONLY from jd_experience_extractor.py.

    Never use Qwen's experience values here.
    """

    experience = experience or {}

    def clean_range(value):

        if not isinstance(value, dict):
            return None

        minimum = value.get("minimum_months")
        maximum = value.get("maximum_months")

        if minimum is not None:

            if not isinstance(minimum, int) or minimum < 0:
                minimum = None

        if maximum is not None:

            if not isinstance(maximum, int) or maximum < 0:
                maximum = None

        if minimum is None and maximum is None:
            return None

        if (
            minimum is not None
            and maximum is not None
            and maximum < minimum
        ):

            return None

        return {
            "minimum_months": minimum,
            "maximum_months": maximum
        }

    return {
        "professional": clean_range(
            experience.get("professional")
        ),

        "internship": clean_range(
            experience.get("internship")
        ),

        "alternative_paths": clean_list(
            experience.get("alternative_paths", [])
        )
    }


# ==================================================
# 5. EXPERIENCE TEXT CLEANUP
# ==================================================

def is_experience_text(value):

    pattern = (
        r"\b\d+\s*"
        r"(?:(?:[-–—]|to)\s*\d+|\+|or\s+more)?\s*"
        r"(?:years?|yrs?|months?|mos?)\b"
        r".*\bexperience\b"
    )

    return bool(
        re.search(
            pattern,
            value,
            re.IGNORECASE
        )
    )


def is_education_text(value):

    if not isinstance(value, str):
        return False

    return bool(
        re.search(
            r"\b("
            r"bachelor(?:'s)?\s+degree|"
            r"master(?:'s)?\s+degree|"
            r"undergraduate\s+degree|"
            r"graduate\s+degree|"
            r"degree\s+in\s+|"
            r"b\.?tech\b|"
            r"b\.?e\.?\b|"
            r"m\.?tech\b|"
            r"m\.?e\.?\b"
            r")",
            value,
            re.IGNORECASE
        )
    )


def is_experience_requirement_text(value):

    if not isinstance(value, str):
        return False

    return bool(
        re.search(
            r"\bexperience\s+"
            r"(developing|building|designing|"
            r"implementing|maintaining|managing|"
            r"working|leading|creating)\b",
            value,
            re.IGNORECASE
        )
    )

# ==================================================
# 6. CERTIFICATION NORMALIZATION
# ==================================================

def is_certification_text(value):

    return bool(
        re.search(
            r"\b(certified|certification|certifications|"
            r"certificate|certificates)\b",
            value,
            re.IGNORECASE
        )
    )
def remove_certification_sentences(text):
    if not text:
        return ""

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    filtered_sentences = [
        sentence
        for sentence in sentences
        if not is_certification_text(sentence)
    ]

    return " ".join(filtered_sentences)

def normalize_certifications(certifications):

    return clean_list(certifications)


# ==================================================
# 7. JD SECTION EXTRACTION
# ==================================================

def extract_jd_sections(job_description):

    sections = {
        "general": [],
        "required": [],
        "preferred": [],
        "responsibilities": [],
        "additional": []
    }

    heading_patterns = {
        "required": [
            r"required qualifications?",
            r"minimum qualifications?",
            r"mandatory requirements?",
            r"basic qualifications?",
            r"required skills",
            r"required experience",
            r"what you'll need",
            r"what you will need",
            r"what we're looking for",
            r"what we are looking for",
            r"what you'll bring",
            r"what you will bring",
            r"who you are",
            r"qualifications",
            r"requirements"
        ],

        "preferred": [
            r"preferred qualifications?",
            r"preferred requirements?",
            r"preferred skills",
            r"preferred experience",
            r"desired qualifications?",
            r"nice[- ]to[- ]have",
            r"good[- ]to[- ]have",
            r"bonus qualifications?",
            r"bonus points",
            r"desirable qualifications?",
            r"optional qualifications?"
        ],

        "responsibilities": [
            r"responsibilities",
            r"key responsibilities",
            r"job responsibilities",
            r"duties",
            r"what you'll do",
            r"what you will do",
            r"key activities",
            r"your role",
            r"role and responsibilities"
        ],

        "additional": [
            r"additional requirements?",
            r"other requirements?",
            r"work conditions",
            r"employment details",
            r"job details",
            r"location and work mode"
        ]
    }

    current_section = "general"

    detected_required = False
    detected_preferred = False

    # --------------------------------------------------
    # 1. Detect headings and collect source lines
    # --------------------------------------------------

    for line in job_description.splitlines():

        original_line = line.strip()

        if not original_line:
            continue

        cleaned = re.sub(
            r"^[\s#>*\-•]+",
            "",
            original_line
        ).strip()

        cleaned = cleaned.strip("*_` :")

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned
        ).casefold().rstrip(":.")

        detected_heading = None

        if len(cleaned.split()) <= 10:

            for section_name, patterns in heading_patterns.items():

                if any(
                    re.fullmatch(pattern, cleaned, re.IGNORECASE)
                    for pattern in patterns
                ):

                    detected_heading = section_name
                    break

        if detected_heading:

            current_section = detected_heading

            if detected_heading == "required":
                detected_required = True

            elif detected_heading == "preferred":
                detected_preferred = True

            continue

        sections[current_section].append(original_line)

    # --------------------------------------------------
    # 2. Sentence-level required/preferred classification
    # --------------------------------------------------

    def classify_general_content(text):

        required_items = []
        preferred_items = []
        general_items = []

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            lower = sentence.casefold()

            preferred_match = re.search(
                r"\b(preferred|preferably|ideally|"
                r"desired|desirable|nice[- ]to[- ]have|"
                r"good[- ]to[- ]have|bonus|optional)\b",
                lower
            )

            required_match = re.search(
                r"\b(required|must|required to|"
                r"mandatory|minimum|need to|"
                r"should have|essential)\b",
                lower
            )

            if preferred_match and not required_match:

                preferred_items.append(sentence)

            elif required_match and not preferred_match:

                required_items.append(sentence)

            elif preferred_match and required_match:

                # Prefer the first explicit qualification signal.
                if preferred_match.start() < required_match.start():
                    preferred_items.append(sentence)
                else:
                    required_items.append(sentence)

            else:

                general_items.append(sentence)

        return required_items, preferred_items, general_items

    # --------------------------------------------------
    # 3. Classify general content when headings are absent
    # --------------------------------------------------

    if not detected_required and not detected_preferred:

        general_text = "\n".join(sections["general"])

        required_items, preferred_items, remaining_items = (
            classify_general_content(general_text)
        )

        sections["required"].extend(required_items)
        sections["preferred"].extend(preferred_items)

        # Unclassified content defaults to required context.
        sections["required"].extend(remaining_items)

        sections["general"] = []

    else:

        # If explicit qualification headings exist,
        # classify only general content using sentence signals.
        general_text = "\n".join(sections["general"])

        required_items, preferred_items, remaining_items = (
            classify_general_content(general_text)
        )

        sections["required"].extend(required_items)
        sections["preferred"].extend(preferred_items)
        sections["general"] = remaining_items

    # --------------------------------------------------
    # 4. Return structured sections
    # --------------------------------------------------

    return {
        key: "\n".join(value).strip()
        for key, value in sections.items()
    }



# ==================================================
# 8. CATEGORY NORMALIZATION
# ==================================================


def normalize_category(
    category,
    experience_data,
    education_data
):

    category = category or {}
    education_data = education_data or {}

    # ----------------------------------------------
    # 1. Technical skills
    # ----------------------------------------------

    raw_technical_skills = clean_list(
        category.get("technical_skills", [])
    )

    misplaced_certifications = [
        item
        for item in raw_technical_skills
        if is_certification_text(item)
    ]

    # Move experience statements out of skills.
    misplaced_experience = [
        item
        for item in raw_technical_skills
        if is_experience_requirement_text(item)
    ]

    technical_skills = normalize_skill_names(
        [
            item
            for item in raw_technical_skills
            if not is_certification_text(item)
            and not is_experience_requirement_text(item)
        ]
    )

    technical_skills = [
        skill
        for skill in technical_skills
        if not is_experience_text(skill)
    ]

    # ----------------------------------------------
    # 2. Non-technical skills
    # ----------------------------------------------

    non_technical_skills = clean_list(
        category.get("non_technical_skills", [])
    )

    # ----------------------------------------------
    # 3. Certifications
    # ----------------------------------------------

    existing_other_requirements = clean_list(
        category.get("other_requirements", [])
    )

    misplaced_other_certifications = [
        item
        for item in existing_other_requirements
        if is_certification_text(item)
    ]

    certifications = normalize_certifications(
        clean_list(
            category.get("certifications", [])
        )
        + misplaced_certifications
        + misplaced_other_certifications
    )

    # ----------------------------------------------
    # 4. Other requirements
    # ----------------------------------------------

    other_requirements = [
        item
        for item in existing_other_requirements
        if not is_certification_text(item)
        and not is_experience_text(item)
        and not is_experience_requirement_text(item)
        and not is_education_text(item)
    ]

    # Add misplaced experience expectations.
    other_requirements.extend(
        misplaced_experience
    )

    # Add non-technical skills.
    other_requirements.extend(
        non_technical_skills
    )

    # Remove misplaced certifications from
    # non-technical skills too.
    other_requirements = [
        item
        for item in other_requirements
        if not is_certification_text(item)
        and not is_experience_text(item)
        and not is_education_text(item)
    ]

    # Remove exact technical skills already represented.
    technical_skill_set = {
        skill.casefold().strip()
        for skill in technical_skills
    }

    other_requirements = [
        item
        for item in other_requirements
        if item.casefold().strip() not in technical_skill_set
    ]

    other_requirements = deduplicate_requirements(
        other_requirements
    )

    # ----------------------------------------------
    # 5. Job conditions
    # ----------------------------------------------

    job_conditions = deduplicate_requirements(
        category.get("job_conditions", [])
    )

    # ----------------------------------------------
    # 6. Education
    # ----------------------------------------------

    qwen_education = normalize_education(
        category.get("education", {})
    )

    degrees = (
        education_data.get("degree")
        or qwen_education["degree"]
    )

    branches = (
        education_data.get("branch")
        or qwen_education["branch"]
    )

    education = {
        "degree": clean_list(degrees),
        "branch": clean_list(branches),
        "graduation_year": qwen_education[
            "graduation_year"
        ]
    }

    # ----------------------------------------------
    # 7. Final category
    # ----------------------------------------------

    return {
        "skills": technical_skills,
        "education": education,
        "experience": normalize_experience(
            experience_data
        ),
        "certifications": certifications,
        "other_requirements": other_requirements,
        "job_conditions": job_conditions
    }


def deduplicate_requirements(items):

    unique_items = []
    seen = set()

    for item in clean_list(items):

        normalized = item.casefold().strip()

        normalized = re.sub(
            r"^(strong|good|excellent|ability to|"
            r"capability to)\s+",
            "",
            normalized
        )

        normalized = re.sub(
            r"[^\w\s+#]",
            " ",
            normalized
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized
        ).strip()

        if normalized not in seen:
            seen.add(normalized)
            unique_items.append(item)

    return unique_items

# ==================================================
# 9. JD EXTRACTION
# ==================================================

def extract_jd_requirements(job_description: str) -> dict:

    if not job_description or not job_description.strip():

        raise ValueError(
            "Job description cannot be empty."
        )
        # ----------------------------------------------
    # Check JD extraction cache
    # ----------------------------------------------

    cache_path = get_jd_cache_path(job_description)

    cached_result = load_jd_cache(cache_path)

    if cached_result is not None:

        print("JD extraction: CACHE HIT")

        return cached_result

    print("JD extraction: CACHE MISS")

    # ----------------------------------------------
    # Extract JD sections
    # ----------------------------------------------

    jd_sections = extract_jd_sections(
        job_description
    )
    print("\n========== JD SECTIONS ==========")
    print(json.dumps(jd_sections, indent=4))
    # ----------------------------------------------
    # Initialize Qwen
    # ----------------------------------------------

    llm = ChatOllama(
        model=JD_MODEL_NAME,
        temperature=0,
        num_predict=4096,
        keep_alive="30m"
    )

    structured_llm = llm.with_structured_output(
        JDExtraction,
        method="json_schema"
    )

    # ----------------------------------------------
    # Extraction prompt
    # ----------------------------------------------

    
    
    prompt = f"""
You are an expert job description requirement extractor.

Your task is to extract requirements accurately from the
provided SOURCE JOB DESCRIPTION.

SOURCE JOB DESCRIPTION:

GENERAL:
<<<
{jd_sections["general"]}
>>>

REQUIRED QUALIFICATIONS:
<<<
{jd_sections["required"]}
>>>

PREFERRED QUALIFICATIONS:
<<<
{jd_sections["preferred"]}
>>>

RESPONSIBILITIES:
<<<
{jd_sections["responsibilities"]}
>>>

ADDITIONAL REQUIREMENTS:
<<<
{jd_sections["additional"]}
>>>

Return TWO categories:
1. REQUIRED
2. PREFERRED

For EACH category, extract:

A. TECHNICAL SKILLS

Include explicitly mentioned:
- Programming languages
- Frameworks and libraries
- Databases
- Developer tools
- Cloud platforms
- Technical concepts
- Technical methodologies
- Domain-specific technical knowledge

Extract every explicitly mentioned technical skill separately.

When a sentence mentions multiple independent technical
skills, extract each skill individually.

Do not omit a technical concept simply because it appears
alongside another skill in the same sentence.

Preserve both the specific tool and the broader technical
concept when both are explicitly mentioned.
Extract every explicitly mentioned technical skill separately.

When a sentence mentions multiple independent technical
skills, extract each skill individually.

Do not omit a technical concept simply because it appears
alongside another skill in the same sentence.

Preserve both the specific tool and the broader technical
concept when both are explicitly mentioned.
Do not classify experience expectations or responsibilities
as technical skills.

For example:
"Experience developing scalable and maintainable backend
applications" belongs in other_requirements, not skills.

Do not split a single requirement into multiple skill fragments.
Preserve the complete original requirement.

B. NON-TECHNICAL SKILLS

Include explicitly mentioned:
- Communication abilities
- Teamwork and collaboration
- Leadership
- Problem-solving abilities
- Analytical abilities
- Adaptability
- Time management
- Interpersonal and behavioral abilities
- Other workplace abilities


C. CERTIFICATIONS

Extract every explicitly mentioned professional certification,
professional certificate, or industry-recognized credential.

IMPORTANT RULES:

1. Extract certifications from both REQUIRED and PREFERRED
   qualification sections.

2. Preserve the original qualification category:
   - Certifications under REQUIRED QUALIFICATIONS
     must go into required.certifications.
   - Certifications under PREFERRED QUALIFICATIONS
     must go into preferred.certifications.

3. Do not ignore a certification because it is described
   as optional, preferred, equivalent, or desirable.

4. Include the complete certification name and any
   equivalent-certification wording.

5. Example:
   "AWS Certified Developer or an equivalent cloud
   certification" must be extracted as one certification.

6. Do not classify technical skills, platforms, tools,
   or general experience as certifications.

7. Do not move certifications between REQUIRED and PREFERRED.


D. EDUCATION

Extract:
- Degree
- Branch or field of study
- Graduation year, if explicitly specified


E. OTHER REQUIREMENTS

Include candidate qualifications and expectations such as:

- Job responsibilities
- Duties and activities
- Work expectations
- Technical responsibilities
- Problem-solving abilities
- Communication and collaboration
- Teamwork and analytical abilities
- Other explicit candidate requirements that do not
  belong in the previous categories

Do not include employment conditions in this category.

F. JOB CONDITIONS

Include employment and job arrangement information such as:

- Full-time or part-time employment
- Work location or city
- Work mode: office-based, remote or hybrid
- Contract or permanent employment
- Shift requirements
- Travel requirements
- Other employment arrangements

These describe the job arrangement, not candidate qualifications.

STRICT CLASSIFICATION:

1. Keep job conditions only in job_conditions.
2. Keep candidate responsibilities and expectations in
   other_requirements.
3. Do not move communication, teamwork, problem-solving
   or other candidate skills into job_conditions.
4. Do not duplicate the same item across both categories.
5. Preserve required/preferred section placement.



STRICT CLASSIFICATION RULES:

1. SECTION ISOLATION

Treat REQUIRED QUALIFICATIONS and PREFERRED QUALIFICATIONS
as separate and independent sources.

Extract each requirement from the section where it appears.

A requirement extracted from REQUIRED QUALIFICATIONS
must go into REQUIRED only.

A requirement extracted from PREFERRED QUALIFICATIONS
must go into PREFERRED only.

Never copy a requirement from one section into the other.

Do not classify a requirement as required merely because
it is important for the job.

Do not classify a requirement as preferred merely because
it is commonly considered optional.

2. SECTION PRIORITY

When both qualification sections contain explicit headings,
their section placement has priority over general context.

RESPONSIBILITIES SECTION:

The RESPONSIBILITIES source section must always be examined.

Extract every explicit responsibility and duty into
other_requirements.

If a responsibility is also explicitly mentioned under
PREFERRED QUALIFICATIONS, place it under PREFERRED.

Otherwise, place responsibilities under REQUIRED.

Do not ignore the RESPONSIBILITIES source section merely
because it is separate from REQUIRED QUALIFICATIONS.

ADDITIONAL REQUIREMENTS SECTION:

Examine the ADDITIONAL REQUIREMENTS source section.

Candidate qualifications and expectations belong in
REQUIRED.other_requirements unless explicitly marked preferred.

Employment conditions belong in job_conditions.

General information must not be used to move a requirement
between REQUIRED and PREFERRED.

3. NO CROSS-CATEGORY DUPLICATION

Do not duplicate the same requirement across REQUIRED
and PREFERRED.

If the same requirement is explicitly stated in both sections,
preserve it in both because the source explicitly requires
both classifications.

4. SKILL CLASSIFICATION

Technical skills belong only in technical_skills.

Non-technical skills belong only in non_technical_skills.

Technical skills include programming languages, frameworks,
libraries, databases, developer tools, cloud platforms,
technical concepts and technical methodologies.

Non-technical skills include behavioral, interpersonal,
communication, analytical and workplace abilities.

Examples of non-technical skills:
- Problem-solving
- Debugging
- Analytical thinking
- Communication
- Collaboration
- Teamwork
- Leadership
- Adaptability
- Time management

Never classify a non-technical skill as a technical skill,
even when it appears in a technical job description.

Do not classify responsibilities or job duties as skills.

5. CERTIFICATIONS

Keep certification names in certifications.

Never classify certifications as technical skills.

Preserve the category of the section where the certification
appears.

6. RESPONSIBILITIES

Extract responsibilities into other_requirements.

Do not classify technical responsibilities as technical skills
merely because they mention technologies.

7. ADDITIONAL REQUIREMENTS

Extract employment conditions, work location,
work mode and other job arrangements into job_conditions.

Extract additional candidate qualifications and expectations
into other_requirements.

8. EXPERIENCE

Do not extract experience durations as skills or
other_requirements.

Experience duration is extracted separately by Python.

9. ALTERNATIVES

Preserve OR alternatives together where appropriate.

For independent technical skills connected by AND,
extract them separately.

10. SOURCE ACCURACY

- Extract only information explicitly stated in the JD.
- Do not invent or infer requirements.
- Do not copy examples from these instructions.
- Avoid duplicate items.
- Preserve the original meaning.
- If a category has no items, return an empty list.
- Do not omit explicit requirements.

Return only the structured result matching the schema.
"""


    # ----------------------------------------------
    # Run Qwen extraction
    # ----------------------------------------------

    started = time.time()

    result = structured_llm.invoke(prompt)

    print(
        f"Qwen JD extraction time: "
        f"{time.time() - started:.2f} seconds"
    )

    if hasattr(result, "model_dump"):

        data = result.model_dump()

    else:

        data = result.dict()

    # ----------------------------------------------
    # Deterministic experience extraction
    # ----------------------------------------------

    experience_data = extract_jd_experience(
        job_description
    )

    # ----------------------------------------------
    # Deterministic education extraction
    # ----------------------------------------------

    education_data = extract_jd_education(
        job_description
    )

        # ----------------------------------------------
    # Final result
    # ----------------------------------------------

    required = normalize_category(
        data.get("required", {}),
        experience_data.get("required", {}),
        education_data.get("required", {})
    )

    preferred = normalize_category(
        data.get("preferred", {}),
        experience_data.get("preferred", {}),
        education_data.get("preferred", {})
    )

    # ----------------------------------------------
    # Validate skills against original JD sections
    # ----------------------------------------------

    required_skill_source = (
    jd_sections.get("required")
    or jd_sections.get("general", "")
)

    required_skill_source = remove_certification_sentences(
    required_skill_source
)

    required["skills"] = filter_items_by_source(
    required["skills"],
    required_skill_source
)

    preferred_skill_source = (
    jd_sections.get("preferred")
    or jd_sections.get("general", "")
)

    preferred_skill_source = remove_certification_sentences(
    preferred_skill_source
)

    preferred["skills"] = filter_items_by_source(
    preferred["skills"],
    preferred_skill_source
)
    

    # ----------------------------------------------
    # Validate certifications against original sections
    # ----------------------------------------------

    required["certifications"] = filter_items_by_source(
        required["certifications"],
        jd_sections.get("required", "")
    )

    preferred["certifications"] = filter_items_by_source(
        preferred["certifications"],
        jd_sections.get("preferred", "")
    )

    # ----------------------------------------------
    # Final output
    # ----------------------------------------------

    final_result = {
        "required": required,
        "preferred": preferred
    }

    save_jd_cache(
        cache_path,
        final_result
    )

    return final_result

