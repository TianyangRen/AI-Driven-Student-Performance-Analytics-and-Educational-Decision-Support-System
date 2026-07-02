import { theme as antdTheme } from 'antd';
import { palette, radius } from './tokens';

/**
 * Ant Design v5 dark cockpit theme.
 * Injected via ConfigProvider to unify the look of all antd components.
 */
export const cockpitTheme = {
  algorithm: antdTheme.darkAlgorithm,
  token: {
    colorPrimary: palette.primary,
    colorInfo: palette.primary,
    colorSuccess: palette.success,
    colorWarning: palette.warning,
    colorError: palette.danger,

    colorBgBase: palette.bgBase,
    colorTextBase: palette.textPrimary,
    colorBgContainer: palette.surfaceSolid,
    colorBgElevated: '#152352',
    colorBorder: palette.border,
    colorBorderSecondary: palette.border,

    colorText: palette.textPrimary,
    colorTextSecondary: palette.textSecondary,
    colorTextTertiary: palette.textMuted,
    colorTextQuaternary: palette.textMuted,

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
      itemSelectedBg: 'rgba(56,189,248,0.16)',
      itemSelectedColor: '#fff',
      itemColor: palette.textSecondary,
      itemHoverColor: '#fff',
      itemHoverBg: 'rgba(56,189,248,0.08)',
      itemHeight: 46,
      itemMarginInline: 10,
      itemBorderRadius: 10,
    },
    Card: {
      colorBgContainer: palette.surface,
      headerBg: 'transparent',
      headerFontSize: 15,
      paddingLG: 20,
    },
    Table: {
      colorBgContainer: 'transparent',
      headerBg: 'rgba(31,47,92,0.55)',
      headerColor: palette.textSecondary,
      rowHoverBg: 'rgba(56,189,248,0.07)',
      borderColor: palette.border,
      headerSplitColor: 'transparent',
    },
    Statistic: {
      contentFontSize: 30,
    },
    Input: { colorBgContainer: 'rgba(10,19,48,0.6)' },
    InputNumber: { colorBgContainer: 'rgba(10,19,48,0.6)' },
    Select: { colorBgContainer: 'rgba(10,19,48,0.6)' },
    Modal: { contentBg: '#0f1c43', headerBg: '#0f1c43' },
    Segmented: {
      trackBg: 'rgba(10,19,48,0.6)',
      itemSelectedBg: 'rgba(56,189,248,0.2)',
    },
  },
};
