
import { useState } from "react";
import {
  FileText,
  Upload,
  BriefcaseBusiness,
  Sparkles,
  BarChart3,
  CheckCircle2,
  AlertCircle,
  LoaderCircle,
  RotateCcw,
  Target,
} from "lucide-react";

import { analyzeResume } from "./services/api";
import ScoreCard from "./components/ScoreCard";
import RequirementSection from "./components/RequirementSection";
import ExperienceCard from "./components/ExperienceCard";
import Suggestions from "./components/Suggestions";

import "./App.css";

const getScoreTone = (score) => {
  if (score == null) return "unavailable";
  if (score >= 80) return "strong";
  if (score >= 60) return "moderate";
  if (score >= 40) return "low";
  return "weak";
};

function App() {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState(null);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) return;

    const allowedExtensions = [".pdf", ".docx"];
    const fileName = selectedFile.name.toLowerCase();

    const isValidFile = allowedExtensions.some((extension) =>
      fileName.endsWith(extension)
    );

    if (!isValidFile) {
      setError("Please upload a PDF or DOCX resume.");
      setFile(null);
      event.target.value = "";
      return;
    }

    setFile(selectedFile);
    setError("");
    setResults(null);
  };

  const handleAnalyze = async (event) => {
    event.preventDefault();

    if (!file) {
      setError("Please upload your resume first.");
      return;
    }

    if (!jd.trim()) {
      setError("Please enter the job description.");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const data = await analyzeResume(file, jd);
      setResults(data);

      setTimeout(() => {
        document.getElementById("results")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    } catch (err) {
      console.error("Resume analysis failed:", err);

      setError(
        err.response?.data?.detail ||
          "Something went wrong while analyzing your resume. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setJd("");
    setResults(null);
    setError("");

    const fileInput = document.getElementById("resume-upload");
    if (fileInput) fileInput.value = "";

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const rawScore = results?.ats_score?.overall_score;

  const score =
    rawScore != null && !Number.isNaN(Number(rawScore))
      ? Number(rawScore)
      : null;

  const scoreTone = getScoreTone(score);
  const rating = results?.ats_score?.rating || "Not available";

  const experience = results?.experience_analysis || {};

  const suggestions = Array.isArray(results?.suggestions)
    ? results.suggestions
    : [];

  return (
    <div className="app">
      {/* NAVBAR */}
      <nav className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <FileText size={22} />
          </div>
          <span>ResumeIQ</span>
        </div>

        <div className="navbar-label">
          Smart Resume Analysis
        </div>
      </nav>

      {/* MAIN CONTAINER */}
      <main className="main-container">
        {/* HERO */}
        <section className="hero">
          <div className="hero-badge">
            <Sparkles size={15} />
            <span>AI-Powered Resume Analysis</span>
          </div>

          <h1>
            Make Your Resume
            <span>Job-Ready.</span>
          </h1>

          <p>
            Analyze your resume against a job description, understand your
            strengths, identify missing requirements, and get actionable
            suggestions to improve your chances.
          </p>
        </section>

        {/* ANALYZER FORM */}
        <form className="analyzer-form" onSubmit={handleAnalyze}>
          <div className="form-grid">
            {/* RESUME UPLOAD */}
            <div className="form-card">
              <div className="form-heading">
                <div className="form-icon upload-icon">
                  <FileText size={19} />
                </div>

                <div>
                  <h3>Upload Your Resume</h3>
                  <p>Upload your resume in PDF or DOCX format.</p>
                </div>
              </div>

              <label
                htmlFor="resume-upload"
                className={`upload-area ${file ? "file-selected" : ""}`}
              >
                <input
                  id="resume-upload"
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleFileChange}
                />

                {file ? (
                  <div className="file-info">
                    <div className="upload-icon">
                      <FileText size={27} />
                    </div>

                    <div className="file-details">
                      <strong>{file.name}</strong>
                      <span>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>

                    <CheckCircle2
                      className="file-success-icon"
                      size={22}
                    />
                  </div>
                ) : (
                  <>
                    <Upload size={28} />

                    <strong>Click to upload your resume</strong>

                    <span>PDF or DOCX format</span>
                  </>
                )}
              </label>

              {file && (
                <button
                  type="button"
                  className="remove-file"
                  onClick={() => {
                    setFile(null);
                    const input =
                      document.getElementById("resume-upload");
                    if (input) input.value = "";
                  }}
                >
                  Remove selected file
                </button>
              )}
            </div>

            {/* JOB DESCRIPTION */}
            <div className="form-card">
              <div className="form-heading">
                <div className="form-icon jd-icon">
                  <BriefcaseBusiness size={19} />
                </div>

                <div>
                  <h3>Job Description</h3>
                  <p>Paste the job description you want to match.</p>
                </div>
              </div>

              <textarea
                className="jd-input"
                placeholder="Paste the complete job description here..."
                value={jd}
                onChange={(event) => {
                  setJd(event.target.value);
                  setError("");
                }}
                rows={10}
              />

              <div className="textarea-footer">
                <span>{jd.length} characters</span>
              </div>
            </div>
          </div>

          {/* ERROR */}
          {error && (
            <div className="error-message">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {/* ANALYZE BUTTON */}
          <button
            type="submit"
            className="analyze-button"
            disabled={loading}
          >
            {loading ? (
              <>
                <LoaderCircle size={19} className="spin" />
                Analyzing Resume...
              </>
            ) : (
              <>
                <Sparkles size={19} />
                Analyze My Resume
              </>
            )}
          </button>
        </form>

        {/* RESULTS */}
        {results && (
          <section className="results-section" id="results">
            <div className="results-header">
              <div>
                <span className="eyebrow">ANALYSIS COMPLETE</span>
                <h2>Your Resume Analysis</h2>
                <p>
                  Here's how your resume matches the job description.
                </p>
              </div>

              <button
                type="button"
                className="reset-button"
                onClick={handleReset}
              >
                <RotateCcw size={16} />
                New Analysis
              </button>
            </div>

            {/* ATS SCORE */}
            <div className="results-section-heading">
              <BarChart3 size={20} />
              <h3>Overall ATS Match</h3>
            </div>

            <ScoreCard
              score={score}
              scoreTone={scoreTone}
              rating={rating}
            />

            {/* REQUIREMENTS */}
            <div className="results-section-heading">
              <Target size={20} />
              <h3>Requirement Analysis</h3>
            </div>

            <div className="requirements-grid">
              <RequirementSection
                title="Matching Requirements"
                icon={CheckCircle2}
                matched={results.matching_requirements || {}}
                missing={{}}
              />

              <RequirementSection
                title="Missing Requirements"
                icon={AlertCircle}
                matched={{}}
                missing={results.missing_requirements || {}}
              />
            </div>

            {/* EXPERIENCE */}
            <div className="results-section-heading">
              <BriefcaseBusiness size={20} />
              <h3>Experience Analysis</h3>
            </div>

            <div className="experience-grid">
              <ExperienceCard
                title="Professional Experience"
                months={experience.professional?.duration_months}
                emoji="💼"
              />

              <ExperienceCard
                title="Internship Experience"
                months={experience.internship?.duration_months}
                emoji="🎯"
              />
            </div>

            {/* SUGGESTIONS */}
            <Suggestions suggestions={suggestions} />
          </section>
        )}
      </main>

      {/* FOOTER */}
      <footer className="footer">
        <p>
          <span>ResumeIQ</span> · AI-Powered Resume Analysis
        </p>
        <p>
          Built to help you move one step closer to your next opportunity.
        </p>
      </footer>
    </div>
  );
}

export default App;
