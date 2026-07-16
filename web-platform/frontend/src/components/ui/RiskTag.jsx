import { RISK_META } from '../../theme/tokens';
import { useI18n } from '../../contexts/PreferencesContext.jsx';

/**
 * RiskTag — risk-level pill (HIGH / MEDIUM / LOW) with semantic color and glow.
 */
export default function RiskTag({ level, size = 'default' }) {
  const { t } = useI18n();
  const key = RISK_META[level] ? level : 'LOW';
  const meta = RISK_META[key];
  const pad = size === 'small' ? '1px 9px' : '3px 12px';
  const fontSize = size === 'small' ? 11 : 12;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: pad,
        fontSize,
        fontWeight: 600,
        lineHeight: 1.4,
        color: meta.color,
        background: `${meta.color}1f`,
        border: `1px solid ${meta.color}55`,
        borderRadius: 999,
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: meta.color,
          boxShadow: `0 0 8px ${meta.glow}`,
        }}
      />
      {t(`risk.${key}`)}
    </span>
  );
}
