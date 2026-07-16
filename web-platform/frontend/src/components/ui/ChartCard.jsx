import ReactECharts from 'echarts-for-react';
import Panel from './Panel';
import { palette } from '../../theme/tokens';

/**
 * ChartCard — renders an ECharts chart inside a glass panel.
 * Unifies chart height, loading and empty-state handling.
 */
export default function ChartCard({
  title,
  subtitle,
  icon,
  extra,
  option,
  height = 300,
  loading = false,
  className = '',
  style,
}) {
  return (
    <Panel title={title} subtitle={subtitle} icon={icon} extra={extra} className={className} style={style}>
      <ReactECharts
        option={option || {}}
        showLoading={loading}
        loadingOption={{
          text: 'Loading',
          color: palette.primary,
          textColor: palette.textSecondary,
          maskColor: `${palette.bgDeep}55`,
        }}
        style={{ height }}
        opts={{ renderer: 'canvas' }}
        notMerge
        lazyUpdate
      />
    </Panel>
  );
}
