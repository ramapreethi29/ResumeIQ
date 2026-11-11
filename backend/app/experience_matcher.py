
import re
from datetime import date


# ==================================================
# 1. DATE EXTRACTION
# ==================================================

MONTHS = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

MONTH_PATTERN = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|"
    r"Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

DATE_TOKEN = (
    rf"(?:\d{{4}}-\d{{1,2}}|"
    rf"(?:{MONTH_PATTERN})\s+\d{{4}})"
)

DATE_RANGE_PATTERN = re.compile(
    rf"({DATE_TOKEN})\s*(?:-|–|—|to)\s*"
    rf"({DATE_TOKEN}|Present|Current|Now)",
    re.IGNORECASE
)


def normalize_date(value: str) -> str:
    """Convert a date into YYYY-MM format."""

    value = value.strip()

    if value.lower() in {"present", "current", "now"}:
        return value.lower()

    if re.fullmatch(r"\d{4}-\d{1,2}", value):
        year, month = map(int, value.split("-"))

        if not 1 <= month <= 12:
            raise ValueError("Month must be between 1 and 12.")

        return f"{year}-{month:02d}"

    parts = value.lower().split()

    if len(parts) != 2 or parts[0] not in MONTHS:
        raise ValueError(f"Unsupported date format: {value}")

    return f"{int(parts[1])}-{MONTHS[parts[0]]}"


# ==================================================
# 2. EXPLICIT DURATION EXTRACTION
# ==================================================
def extract_explicit_duration(text: str):

    text = text.lower()

    year_match = re.search(
        r"(\d+(?:\.\d+)?)\s*-?\s*\+?\s*years?",
        text
    )

    month_match = re.search(
        r"(\d+)\s*-?\s*\+?\s*months?",
        text
    )

    years = float(year_match.group(1)) if year_match else 0
    months = int(month_match.group(1)) if month_match else 0

    if year_match or month_match:
        return round(years * 12) + months

    return None

# ==================================================
# 3. EXPERIENCE TYPE CLASSIFICATION
# ==================================================

def classify_experience_type(title: str, description: str = "") -> str:

    text = f"{title} {description}".lower()

    internship_keywords = [
        "intern",
        "internship",
        "trainee",
        "student intern"
    ]

    if any(keyword in text for keyword in internship_keywords):
        return "internship"

    return "professional"


# ==================================================
# 4. EXPERIENCE RECORD EXTRACTION
# ==================================================
def extract_experience_records(work_experience: str) -> list:

    lines = [
        line.strip()
        for line in work_experience.splitlines()
        if line.strip()
    ]

    headers = []

    for i, line in enumerate(lines):

        if line.startswith(("-", "•", "*")):
            continue

        date_match = DATE_RANGE_PATTERN.search(line)

        # FORMAT 1: Date appears on the title line.
        if date_match and i + 1 < len(lines):

            title_part = line[:date_match.start()].strip()
            title = title_part.split("|")[0].strip(" :-")
            company = lines[i + 1]

            if title and not DATE_RANGE_PATTERN.search(company):
                headers.append({
                    "index": i,
                    "title": title,
                    "company": company,
                    "date_match": date_match,
                    "description_start": i + 2
                })

            continue

        # FORMAT 2: Date appears on a separate line.
        if i + 2 < len(lines):

            title = line
            company = lines[i + 1]
            date_match = DATE_RANGE_PATTERN.search(lines[i + 2])

            if (
                date_match
                and not company.startswith(("-", "•", "*"))
            ):
                headers.append({
                    "index": i,
                    "title": title,
                    "company": company,
                    "date_match": date_match,
                    "description_start": i + 3
                })

    records = []

    for position, header in enumerate(headers):

        if position + 1 < len(headers):
            description_end = headers[position + 1]["index"]
        else:
            description_end = len(lines)

        date_match = header["date_match"]

        start_date = normalize_date(date_match.group(1))
        end_date = normalize_date(date_match.group(2))

        description_lines = lines[
            header["description_start"]:description_end
        ]

        description_text = " ".join(description_lines)

        explicit_duration_months = extract_explicit_duration(
            description_text
        )

        experience_type = classify_experience_type(
            header["title"],
            description_text
        )

        records.append({
            "title": header["title"],
            "company": header["company"],
            "start_date": start_date,
            "end_date": end_date,
            "explicit_duration_months": explicit_duration_months,
            "experience_type": experience_type
        })

    return records
# ==================================================
# 5. CALCULATE DURATION FROM DATES
# ==================================================

def calculate_duration(start: str, end: str) -> int:
    """Calculate inclusive experience duration in months."""

    start_year, start_month = map(int, start.split("-"))

    if end.lower() in {"present", "current", "now"}:
        end_year = date.today().year
        end_month = date.today().month
    else:
        end_year, end_month = map(int, end.split("-"))

    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
        raise ValueError("Month must be between 1 and 12.")

    if (end_year, end_month) < (start_year, start_month):
        raise ValueError("End date cannot be before start date.")

    return (
        (end_year - start_year) * 12
        + (end_month - start_month)
        + 1
    )


def check_duration_discrepancy(
    start_date: str,
    end_date: str,
    explicit_duration_months: int | None
) -> dict:
    """
    Compare date-derived duration with explicit duration.
    Dates always take priority.
    """

    date_duration = calculate_duration(start_date, end_date)

    if explicit_duration_months is None:
        return {
            "date_duration_months": date_duration,
            "explicit_duration_months": None,
            "discrepancy": False,
            "difference_months": None
        }

    difference = abs(date_duration - explicit_duration_months)

    return {
        "date_duration_months": date_duration,
        "explicit_duration_months": explicit_duration_months,
        "discrepancy": difference > 0,
        "difference_months": difference
    }

# ==================================================
# 6. CALCULATE TOTAL DURATION WITHOUT OVERLAP
# ==================================================

def calculate_total_duration(records: list) -> int:
    """
    Calculate total months without double-counting
    overlapping employment periods.

    Expected records:
    [
        {"start": "2023-01", "end": "2024-12"}
    ]
    """

    intervals = []

    for record in records:

        start_year, start_month = map(
            int, record["start"].split("-")
        )

        start_index = start_year * 12 + start_month

        end = record["end"]

        if end.lower() in {"present", "current", "now"}:
            end_year = date.today().year
            end_month = date.today().month
        else:
            end_year, end_month = map(int, end.split("-"))

        if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
            raise ValueError("Month must be between 1 and 12.")

        end_index = end_year * 12 + end_month

        if end_index < start_index:
            raise ValueError("End date cannot be before start date.")

        intervals.append((start_index, end_index))

    if not intervals:
        return 0

    intervals.sort()

    total_months = 0

    current_start, current_end = intervals[0]

    for start, end in intervals[1:]:

        if start <= current_end + 1:
            current_end = max(current_end, end)

        else:
            total_months += current_end - current_start + 1
            current_start, current_end = start, end

    total_months += current_end - current_start + 1

    return total_months


# ==================================================
# 7. GET EXPERIENCE DURATION USING PRIORITY RULES
# ==================================================


def get_experience_duration(records: list) -> dict:
    """
    Calculate experience duration record by record.

    Rules:
    1. Use dates when both start and end dates exist.
    2. Otherwise, use the explicit duration if available.
    3. Merge overlapping date ranges.
    4. Never count an explicit duration for a record
       that already has usable dates.
    """

    date_records = []
    explicit_total = 0

    used_dates = False
    used_explicit = False

    for record in records:

        start = record.get("start_date")
        end = record.get("end_date")

        explicit_duration = record.get(
            "explicit_duration_months"
        )

        # Priority 1: Use dates for this record.
        if start and end:

            date_records.append({
                "start": start,
                "end": end
            })

            used_dates = True

        # Priority 2: Use explicit duration if dates are unavailable.
        elif explicit_duration is not None:

            explicit_total += int(explicit_duration)

            used_explicit = True

    # Merge date-based periods to avoid double-counting overlaps.
    date_total = calculate_total_duration(date_records)

    total_duration = date_total + explicit_total

    if used_dates and used_explicit:
        source = "mixed"

    elif used_dates:
        source = "dates"

    elif used_explicit:
        source = "explicit_statement"

    else:
        return {
            "duration_months": None,
            "source": "not_available"
        }

    return {
        "duration_months": total_duration,
        "source": source
    }


# ==================================================
# 8. CLASSIFY EXPERIENCE AGAINST JD CATEGORIES
# ==================================================

def classify_experience(months: int) -> list:

    classifications = []

    if months <= 12:
        classifications.append("0-1")

    if months <= 24:
        classifications.append("0-2")

    if months >= 12:
        classifications.append("1+")

    if months >= 24:
        classifications.append("2+")

    return classifications


# ==================================================
# 9. MATCH RESUME EXPERIENCE AGAINST JD
# ==================================================

def match_experience_requirement(
    resume_months: int,
    jd_requirement: str
) -> dict:

    requirement = jd_requirement.strip().replace(" ", "")

    if requirement == "0-1":
        meets = resume_months <= 12

    elif requirement == "0-2":
        meets = resume_months <= 24

    elif requirement == "1+":
        meets = resume_months >= 12

    elif requirement == "2+":
        meets = resume_months >= 24

    else:
        return {
            "requirement": jd_requirement,
            "status": "Unsupported requirement"
        }

    return {
        "requirement": jd_requirement,
        "resume_duration_months": resume_months,
        "status": "Meets" if meets else "Does Not Meet"
    }
