
import re

from app.experience_matcher import (
    extract_experience_records, extract_explicit_duration,
    calculate_duration,
    get_experience_duration,
    check_duration_discrepancy
)
from app.education_matcher import extract_education_details
from app.skill_normalizer import extract_resume_skills
# ==================================================
# 1. RESUME SECTION PATTERNS
# ==================================================

SECTION_PATTERNS = {
    "professional_summary": [
        r"professional summary",
        r"career summary",
        r"profile summary",
        r"summary",
        r"objective",
        r"career objective",
        r"profile"
    ],

    "technical_skills": [
        r"technical skills",
        r"skills",
        r"technical expertise",
        r"core competencies",
        r"technologies",
        r"key skills"
    ],

    "work_experience": [
        r"work experience",
        r"work experiences",
        r"professional experience",
        r"professional experiences",
        r"employment history",
        r"experience",
        r"internships",
        r"internship experience",
        r"internship"
    ],

    "projects": [
        r"academic projects",
        r"personal projects",
        r"professional projects",
        r"key projects",
        r"projects"
    ],

    "education": [
        r"educational qualifications",
        r"academic qualifications",
        r"education",
        r"educational background"
    ],

    "certifications": [
        r"certifications",
        r"certificates",
        r"licenses and certifications",
        r"professional certifications"
    ],

    "achievements": [
        r"achievements",
        r"key achievements",
        r"academic achievements",
        r"awards",
        r"honors and awards",
        r"accomplishments"
    ]
}


EMAIL_PATTERN = (
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

PHONE_PATTERN = (
    r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
)


# ==================================================
# 2. NORMALIZE AND IDENTIFY HEADINGS
# ==================================================

def normalize_heading(line: str) -> str:

    line = line.strip().lower()
    line = re.sub(r"[^a-z\s]", "", line)

    return re.sub(r"\s+", " ", line)


def identify_section(line: str):

    normalized_line = normalize_heading(line)

    for section, patterns in SECTION_PATTERNS.items():

        for pattern in patterns:

            if re.fullmatch(pattern, normalized_line):
                return section

    return None


# ==================================================
# 3. EXTRACT PERSONAL INFORMATION
# ==================================================
def extract_personal_info(resume_text: str) -> dict:

    lines = [
        line.strip()
        for line in resume_text.splitlines()
        if line.strip()
    ]

    name = lines[0] if lines else None

    # Extract email
    email_match = re.search(
        r'(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])',
        resume_text
    )

    email = email_match.group(0) if email_match else None

    # Remove accidentally attached phone digits or trailing text
    if email:
        email = re.sub(r'^\+?\d+', '', email)
        email = re.sub(r'(rama)$', '', email, flags=re.IGNORECASE)

    # Extract phone
    phone_match = re.search(PHONE_PATTERN, resume_text)

    phone = phone_match.group(0) if phone_match else None

    return {
        "name": name,
        "email": email,
        "phone": phone
    }


# ==================================================
# 4. EXTRACT RESUME EVIDENCE
# ==================================================

def extract_resume_evidence(sections: dict) -> list:

    evidence = []

    section_prefixes = {
        "technical_skills": "SKILL",
        "professional_summary": "SUMMARY",
        "work_experience": "WORK",
        "projects": "PROJECT",
        "education": "EDUCATION",
        "certifications": "CERTIFICATION",
        "achievements": "ACHIEVEMENT",
        "other": "OTHER"
    }

    counters = {}

    for section, content in sections.items():

        if not content:
            continue

        prefix = section_prefixes.get(section, "OTHER")

        for line in content.splitlines():

            text = line.strip()

            if not text:
                continue

            counters[prefix] = counters.get(prefix, 0) + 1

            evidence_id = (
                f"RES_{prefix}_{counters[prefix]:03d}"
            )

            evidence.append({
                "evidence_id": evidence_id,
                "section": section,
                "text": text
            })

    return evidence


# ==================================================
# 5. EXTRACT EXPERIENCE AND CALCULATE TOTALS
# ==================================================
def extract_experience(work_experience: str) -> dict:

    records = extract_experience_records(work_experience)

    professional_records = []
    internship_records = []

    for record in records:

        record = record.copy()

        start_date = record.get("start_date")
        end_date = record.get("end_date")
        explicit_duration = record.get("explicit_duration_months")

        # Calculate duration only when both dates exist.
        if start_date and end_date:
            date_duration = calculate_duration(
                start_date,
                end_date
            )
        else:
            date_duration = None

        record["date_duration_months"] = date_duration

        # Check discrepancies only when dates and
        # an explicit duration are both available.
        if (
            start_date
            and end_date
            and explicit_duration is not None
        ):
            discrepancy = check_duration_discrepancy(
                start_date,
                end_date,
                explicit_duration
            )

            record["discrepancy"] = discrepancy["discrepancy"]
            record["difference_months"] = discrepancy["difference_months"]

        else:
            record["discrepancy"] = False
            record["difference_months"] = None

        # Separate professional experience and internships.
        if record["experience_type"] == "internship":
            internship_records.append(record)
        else:
            professional_records.append(record)

    # Calculate professional experience.
    professional_duration = get_experience_duration(
        professional_records
    )

    # Calculate internship experience.
    internship_duration = get_experience_duration(
        internship_records
    )

    return {
        "professional": {
            "duration_months": professional_duration["duration_months"],
            "source": professional_duration["source"],
            "records": professional_records
        },

        "internship": {
            "duration_months": internship_duration["duration_months"],
            "source": internship_duration["source"],
            "records": internship_records
        }
    }

# ==================================================
# 6. MAIN RESUME EXTRACTION
# ==================================================
def extract_resume_sections(resume_text: str) -> dict:

    personal_info = extract_personal_info(resume_text)

    sections = {}

    current_section = "other"

    for line in resume_text.splitlines():

        line = line.strip()

        if not line:
            continue

        if personal_info["name"] and line == personal_info["name"]:
            continue

        if personal_info["email"] and personal_info["email"] in line:
            line = line.replace(personal_info["email"], "").strip()

        if personal_info["phone"] and personal_info["phone"] in line:
            line = line.replace(personal_info["phone"], "").strip()

        # Remove empty contact labels.
        if line.lower().strip(": ") in [
            "email",
            "phone",
            "mobile",
            "contact",
            "contact number"
        ]:
            continue

        if not line:
            continue

        detected_section = identify_section(line)

        if detected_section:
            current_section = detected_section
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(line)

    # Convert section lists into strings.
    extracted_sections = {
        section: "\n".join(content).strip()
        for section, content in sections.items()
        if content
    }

    extracted_sections.setdefault("achievements", "")
    extracted_sections.setdefault("other", "")

    technical_skills_text = extracted_sections.get("technical_skills", "")
    normalized_skills = extract_resume_skills(technical_skills_text)
    
    # Generate evidence IDs once.
    evidence = extract_resume_evidence(extracted_sections)

    # Extract work experience.
    work_experience = extracted_sections.get("work_experience", "")
    experience = extract_experience(work_experience)

    # Compare summary experience with date-based experience.
    summary_text = extracted_sections.get("professional_summary", "")

    summary_months = extract_explicit_duration(summary_text)

    professional_months = experience["professional"]["duration_months"]

    if summary_months is not None and professional_months is not None:

        experience["professional"]["summary_comparison"] = {
            "summary_claim_months": summary_months,
            "date_based_months": professional_months,
            "difference_months": abs(
                summary_months - professional_months
            ),
            "discrepancy": summary_months != professional_months
        }

    else:

        experience["professional"]["summary_comparison"] = None

    # Extract education.
    education_text = extracted_sections.get("education", "")

    education = (
        extract_education_details(education_text)
        if education_text
        else {
            "degree": None,
            "branch": None,
            "graduation_year": None
        }
    )

    return {
        "personal_info": personal_info,
        "sections": extracted_sections,
        "normalized_skills": normalized_skills,
        "experience": experience,
        "education": education
    }
