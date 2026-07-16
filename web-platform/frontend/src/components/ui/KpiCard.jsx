import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { palette } from '../../theme/tokens';

/**
 * KpiCard — cockpit key-metric card.
 * Supports icon, accent glow, unit suffix, trend delta and a bottom hint.
 */
export default function KpiCard({
  label,
  value,
  suffix,
  prefix,
  icon,
  color = palette.cyan,
  trend,
  hint,
  style,
}) {
  const trendUp = typeof trend === 'number' && trend >= 0;
  return (
    <div className="cockpit-panel cockpit-panel--hover kpi-card fade-up" style={style}>
      <div className="kpi-card__glow" style={{ background: color }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="kpi-card__label">{label}</span>
        {icon && (
          <span
            className="kpi-card__icon"
            style={{ background: `${color}22`, color, boxShadow: `0 0 18px -6px ${color}` }}
          >
            {icon}
          </span>
        )}
      </div>
      <div>
        <div className="kpi-card__value" style={{ color: palette.textStrong }}>
          {prefix}
          {value}
          {suffix && (
            <span style={{ fontSize: 15, fontWeight: 500, color: palette.textSecondary, marginLeft: 4 }}>
              {suffix}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
          {typeof trend === 'number' && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 2,
                fontSize: 12,
                fontWeight: 600,
                color: trendUp ? palette.success : palette.danger,
              }}
            >
              {trendUp ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              {Math.abs(trend)}%
            </span>
          )}
          {hint && <span style={{ fontSize: 12, color: palette.textMuted }}>{hint}</span>}
        </div>
      </div>
    </div>
  );
}
