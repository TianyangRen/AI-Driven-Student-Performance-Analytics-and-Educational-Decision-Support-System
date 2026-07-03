/**
 * Global design tokens — single source of truth for the data cockpit
 * color system and sizing. Pages, charts and components all reference these.
 */
export const palette = {
  // Background & surfaces
  bgDeep: '#070d20',
  bgBase: '#0a1330',
  surface: 'rgba(20, 32, 66, 0.55)',
  surfaceSolid: '#101b3d',
  surfaceHover: 'rgba(31, 47, 92, 0.7)',
  border: 'rgba(94, 124, 196, 0.22)',
  borderStrong: 'rgba(94, 124, 196, 0.4)',

  // Primary / accent
  primary: '#38bdf8',
  primaryDeep: '#0ea5e9',
  cyan: '#22d3ee',
  violet: '#818cf8',
  indigo: '#6366f1',
  teal: '#2dd4bf',
  gold: '#fbbf24',

  // Text
  textPrimary: '#e8f0ff',
  textSecondary: '#93a7d1',
  textMuted: '#5f739c',

  // Risk semantic colors
  riskHigh: '#ff5d7a',
  riskMedium: '#ffb020',
  riskLow: '#2dd4bf',
  success: '#34d399',
  warning: '#fbbf24',
  danger: '#ff5d7a',
};

export const RISK_META = {
  HIGH: { color: palette.riskHigh, label: 'High', glow: 'rgba(255,93,122,0.45)' },
  MEDIUM: { color: palette.riskMedium, label: 'Medium', glow: 'rgba(255,176,32,0.4)' },
  LOW: { color: palette.riskLow, label: 'Low', glow: 'rgba(45,212,191,0.4)' },
};

// Common chart color palette
export const chartColors = [
  palette.cyan,
  palette.violet,
  palette.gold,
  palette.teal,
  palette.riskHigh,
  palette.indigo,
];

export const radius = {
  sm: 8,
  md: 14,
  lg: 18,
};
