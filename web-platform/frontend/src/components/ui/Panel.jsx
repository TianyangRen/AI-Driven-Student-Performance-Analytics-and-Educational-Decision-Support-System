/**
 * Panel — cockpit glassmorphism container.
 * Replaces antd Card as the unified content panel: optional title,
 * top-right extra actions and hover highlight.
 */
export default function Panel({
  title,
  subtitle,
  extra,
  icon,
  hover = false,
  bodyStyle,
  className = '',
  style,
  children,
}) {
  return (
    <section
      className={`cockpit-panel ${hover ? 'cockpit-panel--hover' : ''} ${className}`}
      style={style}
    >
      {(title || extra) && (
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            padding: '16px 20px',
            borderBottom: '1px solid rgba(94,124,196,0.16)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
            {icon && (
              <span style={{ color: '#38bdf8', fontSize: 18, display: 'inline-flex' }}>{icon}</span>
            )}
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 15, color: '#e8f0ff' }}>{title}</div>
              {subtitle && (
                <div style={{ fontSize: 12, color: '#93a7d1', marginTop: 2 }}>{subtitle}</div>
              )}
            </div>
          </div>
          {extra && <div style={{ flexShrink: 0 }}>{extra}</div>}
        </header>
      )}
      <div style={{ padding: title ? '18px 20px' : 20, ...bodyStyle }}>{children}</div>
    </section>
  );
}
