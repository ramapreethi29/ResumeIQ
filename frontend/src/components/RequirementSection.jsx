
function RequirementSection({ title, icon: Icon, matched, missing }) {
  const isMissing = title.toLowerCase().includes("missing");
  const requirements = isMissing ? missing : matched;

  const categories = [
    { key: "skills", label: "Technical Skills", emoji: "💻" },
    { key: "education", label: "Education", emoji: "🎓" },
    { key: "experience", label: "Experience", emoji: "💼" },
    { key: "certifications", label: "Certifications", emoji: "🏅" },
    { key: "others", label: "Other Requirements", emoji: "📌" },
  ];

  return (
    <div
      className={`requirement-card ${
        isMissing ? "missing-card" : "matching-card"
      }`}
    >
      <div className="section-heading">
        <Icon size={23} />
        <h3>{title}</h3>
      </div>

      {categories.map((category) => {
        const items = requirements?.[category.key] || [];

        return (
          <div className="requirement-category" key={category.key}>
            <h4>
              <span>{category.emoji}</span>
              {category.label}
            </h4>

            {Array.isArray(items) && items.length > 0 ? (
              <div className="requirement-tags">
                {items.map((item, index) => (
                  <span
                    className="requirement-tag"
                    key={`${item}-${index}`}
                  >
                    {typeof item === "string"
                      ? item
                      : item?.name || item?.skill || JSON.stringify(item)}
                  </span>
                ))}
              </div>
            ) : (
              <p className="empty-message">
                No requirements identified
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default RequirementSection;
