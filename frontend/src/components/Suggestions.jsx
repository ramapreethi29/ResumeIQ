
function Suggestions({ suggestions }) {
  return (
    <section className="suggestions-section">
      <div className="suggestions-heading">
        <div className="suggestions-icon">✨</div>

        <div>
          <span className="eyebrow">PERSONALIZED FEEDBACK</span>

          <h3>AI-Powered Resume Improvement Suggestions</h3>

          <p>
            Actionable recommendations to strengthen your resume.
          </p>
        </div>
      </div>

      {suggestions.length > 0 ? (
        <div className="suggestions-list">
          {suggestions.map((suggestion, index) => (
            <div className="suggestion-item" key={index}>
              <div className="suggestion-number">
                {index + 1}
              </div>

              <p>
                {typeof suggestion === "string"
                  ? suggestion
                  : suggestion?.suggestion ||
                    suggestion?.recommendation ||
                    JSON.stringify(suggestion)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-message">
          No suggestions available.
        </p>
      )}
    </section>
  );
}

export default Suggestions;
