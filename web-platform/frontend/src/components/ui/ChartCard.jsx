import ReactECharts from 'echarts-for-react';
import Panel from './Panel';

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
          color: '#38bdf8',
          textColor: '#93a7d1',
          maskColor: 'rgba(7,13,32,0.3)',
        }}
        style={{ height }}
        opts={{ renderer: 'canvas' }}
        notMerge
        lazyUpdate
      />
    </Panel>
  );
}
