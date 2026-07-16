import { theme as antdTheme } from 'antd';
import { COLORS, radius } from './tokens';

/**
 * Ant Design v5 theme builder — returns a dark "cockpit" theme or a light
 * "day" theme depending on `mode`. Injected via ConfigProvider to unify the
 * look of all antd components.
 */
export function buildTheme(mode = 'dark') {
  const isLight = mode === 'light';
  const c = isLight ? COLORS.light : COLORS.dark;

  return {
    algorithm: isLight ? antdTheme.defaultAlgorithm : antdTheme.darkAlgorithm,
    token: {
      colorPrimary: c.primary,
      colorInfo: c.primary,
      colorSuccess: c.success,
      colorWarning: c.warning,
      colorError: c.danger,

      colorBgBase: c.bgBase,
      colorTextBase: c.textPrimary,
      colorBgContainer: c.surfaceSolid,
      colorBgElevated: isLight ? '#ffffff' : '#152352',
      colorBorder: c.border,
      colorBorderSecondary: c.border,

      colorText: c.textPrimary,
      colorTextSecondary: c.textSecondary,
      colorTextTertiary: c.textMuted,
      colorTextQuaternary: c.textMuted,

      borderRadius: radius.md,
      borderRadiusLG: radius.lg,
      borderRadiusSM: radius.sm,

      fontFamily:
        "'Inter', 'HarmonyOS Sans SC', 'PingFang SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      fontSize: 14,
      controlHeight: 38,
      wireframe: false,
    },
    components: {
      Layout: {
        headerBg: 'transparent',
        bodyBg: 'transparent',
        siderBg: 'transparent',
        headerPadding: '0 24px',
      },
      Menu: {
        itemBg: 'transparent',
        darkItemBg: 'transparent',
        darkSubMenuItemBg: 'transparent',
        itemSelectedBg: isLight ? 'rgba(14,165,233,0.12)' : 'rgba(56,189,248,0.16)',
        itemSelectedColor: isLight ? c.primaryDeep : '#fff',
        itemColor: c.textSecondary,
        itemHoverColor: isLight ? c.primaryDeep : '#fff',
        itemHoverBg: isLight ? 'rgba(14,165,233,0.08)' : 'rgba(56,189,248,0.08)',
        itemHeight: 46,
        itemMarginInline: 10,
        itemBorderRadius: 10,
      },
      Card: {
        colorBgContainer: c.surface,
        headerBg: 'transparent',
        headerFontSize: 15,
        paddingLG: 20,
      },
      Table: {
        colorBgContainer: 'transparent',
        headerBg: isLight ? 'rgba(79,106,168,0.10)' : 'rgba(31,47,92,0.55)',
        headerColor: c.textSecondary,
        rowHoverBg: isLight ? 'rgba(14,165,233,0.06)' : 'rgba(56,189,248,0.07)',
        borderColor: c.border,
        headerSplitColor: 'transparent',
      },
      Statistic: {
        contentFontSize: 30,
      },
      Input: { colorBgContainer: isLight ? '#ffffff' : 'rgba(10,19,48,0.6)' },
      InputNumber: { colorBgContainer: isLight ? '#ffffff' : 'rgba(10,19,48,0.6)' },
      Select: { colorBgContainer: isLight ? '#ffffff' : 'rgba(10,19,48,0.6)' },
      Modal: {
        contentBg: isLight ? '#ffffff' : '#0f1c43',
        headerBg: isLight ? '#ffffff' : '#0f1c43',
      },
      Segmented: {
        trackBg: isLight ? 'rgba(79,106,168,0.10)' : 'rgba(10,19,48,0.6)',
        itemSelectedBg: isLight ? 'rgba(14,165,233,0.16)' : 'rgba(56,189,248,0.2)',
      },
    },
  };
}

// Backward-compatible default (dark) theme export.
export const cockpitTheme = buildTheme('dark');
