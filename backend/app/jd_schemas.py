
from pydantic import BaseModel, Field
from typing import Optional


# ==================================================
# 1. EXPERIENCE SCHEMAS
# ==================================================

class ExperienceRange(BaseModel):
    minimum_months: Optional[int] = None
    maximum_months: Optional[int] = None


class ExperienceRequirement(BaseModel):
    professional: Optional[ExperienceRange] = None
    internship: Optional[ExperienceRange] = None
    alternative_paths: list[str] = Field(default_factory=list)


# ==================================================
# 2. EDUCATION SCHEMA
# ==================================================

class EducationRequirement(BaseModel):
    degree: list[str] = Field(default_factory=list)
    branch: list[str] = Field(default_factory=list)
    graduation_year: Optional[int] = None


# ==================================================
# 3. FINAL JD REQUIREMENT SCHEMA
# ==================================================

class RequirementCategory(BaseModel):
    skills: list[str] = Field(default_factory=list)
    education: EducationRequirement = Field(
        default_factory=EducationRequirement
    )
    experience: ExperienceRequirement = Field(
        default_factory=ExperienceRequirement
    )
    certifications: list[str] = Field(default_factory=list)
    other_requirements: list[str] = Field(default_factory=list)
    job_conditions: list[str] = Field(default_factory=list)


class JDRequirements(BaseModel):
    required: RequirementCategory = Field(
        default_factory=RequirementCategory
    )
    preferred: RequirementCategory = Field(
        default_factory=RequirementCategory
    )


# ==================================================
# 4. INTERNAL QWEN EXTRACTION SCHEMAS
# ==================================================

class JDExtractionCategory(BaseModel):
    technical_skills: list[str] = Field(default_factory=list)
    non_technical_skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)

    education: EducationRequirement = Field(
        default_factory=EducationRequirement
    )

    other_requirements: list[str] = Field(default_factory=list)
    job_conditions: list[str] = Field(default_factory=list)


class JDExtraction(BaseModel):
    required: JDExtractionCategory = Field(
        default_factory=JDExtractionCategory
    )

    preferred: JDExtractionCategory = Field(
        default_factory=JDExtractionCategory
    )
