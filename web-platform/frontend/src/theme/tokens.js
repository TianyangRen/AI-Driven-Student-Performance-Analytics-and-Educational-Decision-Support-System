/**
 * Global design tokens — single source of truth for the data cockpit
 * color system and sizing. Pages, charts and components all reference these.
 *
 * Supports two themes (dark "night" / light "day"). The exported `palette`
 * object is mutated in place by `applyColorMode()` so that every module that
 * imported it (inline styles, charts, components) picks up the new values on
 * the next render — the app remounts its routed content on theme change to
 * force that render.
 */

// ---- Dark ("night") theme ----------------------------------------------------
const darkPalette = {
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
  textStrong: '#ffffff',
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

// ---- Light ("day") theme -----------------------------------------------------
const lightPalette = {
  bgDeep: '#eef2fb',
  bgBase: '#f6f8fe',
  surface: 'rgba(255, 255, 255, 0.86)',
  surfaceSolid: '#ffffff',
  surfaceHover: 'rgba(56, 189, 248, 0.08)',
  border: 'rgba(79, 106, 168, 0.22)',
  borderStrong: 'rgba(79, 106, 168, 0.38)',

  primary: '#0ea5e9',
  primaryDeep: '#0284c7',
  cyan: '#0891b2',
  violet: '#6366f1',
  indigo: '#4f46e5',
  teal: '#0d9488',
  gold: '#d97706',

  textStrong: '#0f1e3d',
  textPrimary: '#1b2a4a',
  textSecondary: '#5a6b8c',
  textMuted: '#8391ad',

  riskHigh: '#e11d48',
  riskMedium: '#d97706',
  riskLow: '#0d9488',
  success: '#059669',
  warning: '#d97706',
  danger: '#e11d48',
};

export const COLORS = { dark: darkPalette, light: lightPalette };

/** Mutable, live palette consumed everywhere. Defaults to the dark theme. */
export const palette = { ...darkPalette };

/** Chart color sequence (live binding — reassigned on theme change). */
function buildChartColors(p) {
  return [p.cyan, p.violet, p.gold, p.teal, p.riskHigh, p.indigo];
}
export let chartColors = buildChartColors(palette);

export const RISK_META = {
  HIGH: { color: palette.riskHigh, label: 'High', glow: 'rgba(255,93,122,0.45)' },
  MEDIUM: { color: palette.riskMedium, label: 'Medium', glow: 'rgba(255,176,32,0.4)' },
  LOW: { color: palette.riskLow, label: 'Low', glow: 'rgba(45,212,191,0.4)' },
};

/**
 * Switch the active color mode by mutating the shared palette in place and
 * refreshing derived values so already-imported references stay valid.
 */
export function applyColorMode(mode) {
  const next = mode === 'light' ? lightPalette : darkPalette;
  Object.assign(palette, next);
  chartColors = buildChartColors(palette);
  RISK_META.HIGH.color = palette.riskHigh;
  RISK_META.MEDIUM.color = palette.riskMedium;
  RISK_META.LOW.color = palette.riskLow;
}

export const radius = {
  sm: 8,
  md: 14,
  lg: 18,
};
