import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Form
from pydantic import BaseModel

from app.document_reader import extract_file_text
from app.resume_parser import extract_resume_sections
from app.jd_analyzer import extract_jd_requirements
from app.requirement_matcher import compare_requirements
from app.suggestion_generator import generate_suggestions
from app.ats_scorer import calculate_ats_score
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="ResumeIQ API",
    description="AI-powered Resume Analysis and Job Matching API",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# REQUEST MODELS
# ==================================================

class JDRequest(BaseModel):
    jd: str


# ==================================================
# 1. HEALTH CHECK
# ==================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "ResumeIQ"
    }


# ==================================================
# 2. RESUME ANALYSIS
# ==================================================

@app.post("/resume/analyze")
async def analyze_resume(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported."
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    try:
        resume_text = extract_file_text(
            file.filename,
            file_bytes
        )

        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in the uploaded resume."
            )

        result = extract_resume_sections(resume_text)

        return {
            "filename": file.filename,
            **result
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==================================================
# 3. RESUME DEBUG
# ==================================================

@app.post("/resume/debug")
async def debug_resume(file: UploadFile = File(...)):

    file_bytes = await file.read()

    resume_text = extract_file_text(
        file.filename,
        file_bytes
    )

    return {
        "extracted_text": resume_text
    }


# ==================================================
# 4. JOB DESCRIPTION ANALYSIS
# ==================================================

@app.post("/jd/analyze")
def analyze_job_description(
    jd: str = Body(..., media_type="text/plain")
):

    if not jd.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    try:
        result = extract_jd_requirements(jd)
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==================================================
# 5. COMPLETE RESUME + JD ANALYSIS
# ==================================================

# ==================================================
# 5. COMPLETE RESUME + JD ANALYSIS
# ==================================================

@app.post("/analyze/suggestions")
async def analyze_resume_and_generate_suggestions(
    file: UploadFile = File(...),
    jd: str = Form(...)
):

    # STEP 1: Validate resume file

    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported."
        )

    # STEP 2: Validate job description

    if not jd.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    # STEP 3: Read resume file

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded resume is empty."
        )

    try:

        # STEP 4: Extract resume text

        resume_text = extract_file_text(
            file.filename,
            file_bytes
        )

        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in the uploaded resume."
            )

        # STEP 5: Parse resume

        resume_data = extract_resume_sections(resume_text)

        # STEP 6: Extract JD requirements

        jd_requirements = extract_jd_requirements(jd)

        # STEP 7: Compare resume with JD

        comparison = compare_requirements(
            jd_requirements,
            resume_data
        )

        matching_requirements = comparison["matching_requirements"]
        missing_requirements = comparison["missing_requirements"]

        # STEP 8: Prepare experience analysis

        experience_analysis = resume_data["experience"]

        professional_months = (
            experience_analysis["professional"]["duration_months"]
        )

        required_experience = (
            jd_requirements["required"]["experience"]["professional"]
        )

        preferred_experience = (
            jd_requirements["preferred"]["experience"]["professional"]
        )

        experience_context = {
            "date_based_professional_months": professional_months,
            "required_minimum_months": (
                required_experience["minimum_months"]
                if required_experience else None
            ),
            "required_maximum_months": (
                required_experience["maximum_months"]
                if required_experience else None
            ),
            "preferred_minimum_months": (
                preferred_experience["minimum_months"]
                if preferred_experience else None
            )
        }

        
        # STEP 10: Generate suggestions

        suggestions = generate_suggestions(
            matching_requirements,
            missing_requirements,
            experience_context
        )

        # STEP 11: Calculate ATS score

        ats_score = calculate_ats_score(
            jd_requirements=jd_requirements,
            matching_requirements=matching_requirements,
            missing_requirements=missing_requirements,
            experience_analysis=experience_analysis
        )

        # STEP 12: Return complete analysis

        return {
            "matching_requirements": matching_requirements,
            "missing_requirements": missing_requirements,
            "experience_analysis": experience_analysis,
            "suggestions": suggestions,
            "ats_score": ats_score
        }


    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )
