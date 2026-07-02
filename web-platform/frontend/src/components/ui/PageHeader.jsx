/**
 * PageHeader — unified page title area: gradient accent bar + title/subtitle
 * on the left, action area on the right.
 */
export default function PageHeader({ title, subtitle, extra }) {
  return (
    <div className="page-header fade-up">
      <div style={{ minWidth: 0 }}>
        <h1 className="page-header__title">
          <span className="page-header__accent" />
          {title}
        </h1>
        {subtitle && <div className="page-header__subtitle">{subtitle}</div>}
      </div>
      {extra && <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>{extra}</div>}
    </div>
  );
}
