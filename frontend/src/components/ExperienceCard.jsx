
const formatDuration = (months) => {
  if (months == null || Number.isNaN(Number(months))) {
    return "Not identified";
  }

  const value = Number(months);
  const years = Math.floor(value / 12);
  const remainingMonths = value % 12;

  if (years === 0) return `${remainingMonths} months`;
  if (remainingMonths === 0) return `${years} years`;

  return `${years} years ${remainingMonths} months`;
};

function ExperienceCard({ title, months, emoji }) {
  return (
    <div className="experience-card">
      <div className="experience-icon">{emoji}</div>
      <div>
        <h4>{title}</h4>
        <p>{formatDuration(months)}</p>
      </div>
    </div>
  );
}

export default ExperienceCard;
