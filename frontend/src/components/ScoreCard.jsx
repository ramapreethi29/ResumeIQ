
function ScoreCard({ score, scoreTone, rating }) {
  return (
    <div className="score-card">
      <div className="score-content">
        <span className="eyebrow">YOUR ATS MATCH SCORE</span>

        <h2>
          {score == null ? "N/A" : `${score}/100`}
        </h2>

        <span className={`rating-label ${scoreTone}`}>
          {rating}
        </span>

        <p>
          Your resume's overall match with the job requirements.
        </p>
      </div>

      <div
        className={`score-ring ${scoreTone}`}
        style={{ "--score": `${score ?? 0}%` }}
      >
        <div className="score-ring-inner">
          <strong>{score == null ? "--" : `${score}%`}</strong>
          <span>Match</span>
        </div>
      </div>
    </div>
  );
}

export default ScoreCard;
