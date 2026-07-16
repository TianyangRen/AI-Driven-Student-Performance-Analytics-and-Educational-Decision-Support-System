import * as echarts from 'echarts';
import { palette, chartColors, RISK_META } from './tokens';

/**
 * Shared ECharts cockpit-style config and chart builders.
 * Each build* function returns a complete ECharts option; pages just pass data.
 *
 * NOTE: all palette reads happen at call time (not module load) so charts
 * reflect the active light/dark theme when pages re-render.
 */

function axisCommon() {
  return {
    axisLine: { lineStyle: { color: palette.border } },
    axisLabel: { color: palette.textSecondary, fontSize: 11 },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: palette.border } },
  };
}

function baseTooltip() {
  return {
    backgroundColor: palette.surfaceSolid,
    borderColor: palette.borderStrong,
    borderWidth: 1,
    textStyle: { color: palette.textPrimary, fontSize: 12 },
    padding: [8, 12],
    extraCssText: 'backdrop-filter: blur(6px); border-radius:10px;',
  };
}

function linearGradient(from, to) {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: from },
    { offset: 1, color: to },
  ]);
}

/** Line trend chart (area gradient + glow) */
export function buildTrendChart({ categories, values, name = 'Value', color = palette.cyan, min, max }) {
  return {
    color: chartColors,
    grid: { left: 8, right: 16, top: 28, bottom: 8, containLabel: true },
    tooltip: { ...baseTooltip(), trigger: 'axis' },
    xAxis: { type: 'category', boundaryGap: false, data: categories, ...axisCommon() },
    yAxis: { type: 'value', min, max, ...axisCommon() },
    series: [
      {
        name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: false,
        lineStyle: { width: 3, color, shadowColor: color, shadowBlur: 12 },
        itemStyle: { color, borderColor: '#fff', borderWidth: 1.5 },
        areaStyle: { color: linearGradient(`${color}55`, `${color}05`) },
        emphasis: { focus: 'series', itemStyle: { borderWidth: 2 } },
        data: values,
      },
    ],
  };
}

/** Bar distribution chart (rounded gradient bars) */
export function buildBarChart({ categories, values, color = palette.violet, name = 'Count' }) {
  return {
    grid: { left: 8, right: 16, top: 28, bottom: 8, containLabel: true },
    tooltip: { ...baseTooltip(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: categories, ...axisCommon() },
    yAxis: { type: 'value', ...axisCommon() },
    series: [
      {
        name,
        type: 'bar',
        barWidth: '46%',
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: linearGradient(color, `${color}33`),
        },
        emphasis: { itemStyle: { color: linearGradient('#fff', color) } },
        data: values,
      },
    ],
  };
}

/** Risk share donut chart */
export function buildRiskDonut({ high = 0, medium = 0, low = 0 }) {
  const data = [
    { value: high, name: 'HIGH', itemStyle: { color: RISK_META.HIGH.color } },
    { value: medium, name: 'MEDIUM', itemStyle: { color: RISK_META.MEDIUM.color } },
    { value: low, name: 'LOW', itemStyle: { color: RISK_META.LOW.color } },
  ];
  return {
    tooltip: { ...baseTooltip(), trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      bottom: 0,
      icon: 'circle',
      textStyle: { color: palette.textSecondary, fontSize: 11 },
      formatter: (n) => RISK_META[n]?.label || n,
    },
    series: [
      {
        type: 'pie',
        radius: ['58%', '78%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: false,
        padAngle: 3,
        itemStyle: { borderRadius: 6, borderColor: palette.bgDeep, borderWidth: 2 },
        label: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 6,
          label: { show: true, fontSize: 15, fontWeight: 600, color: palette.textStrong, formatter: '{c}' },
        },
        data,
      },
    ],
  };
}

/** Multi-dimensional radar chart */
export function buildRadarChart({ indicators, values, name = 'Current indicators' }) {
  return {
    tooltip: { ...baseTooltip() },
    radar: {
      indicator: indicators,
      radius: '66%',
      center: ['50%', '52%'],
      axisName: { color: palette.textSecondary, fontSize: 12 },
      splitLine: { lineStyle: { color: palette.border } },
      splitArea: { areaStyle: { color: ['rgba(56,189,248,0.03)', 'rgba(129,140,248,0.05)'] } },
      axisLine: { lineStyle: { color: palette.border } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name,
            symbolSize: 5,
            lineStyle: { color: palette.cyan, width: 2 },
            itemStyle: { color: palette.cyan },
            areaStyle: { color: 'rgba(34,211,238,0.22)' },
          },
        ],
      },
    ],
  };
}

/** Horizontal bar (e.g. SHAP contribution) */
export function buildContribBar({ items }) {
  // items: [{ name, value, positive }]
  const sorted = [...items].sort((a, b) => Math.abs(a.value) - Math.abs(b.value));
  return {
    grid: { left: 8, right: 28, top: 10, bottom: 8, containLabel: true },
    tooltip: { ...baseTooltip(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', ...axisCommon() },
    yAxis: { type: 'category', data: sorted.map((i) => i.name), ...axisCommon() },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        label: {
          show: true,
          position: 'right',
          color: palette.textSecondary,
          fontSize: 11,
          formatter: (p) => p.value.toFixed(2),
        },
        itemStyle: {
          borderRadius: 4,
          color: (p) =>
            sorted[p.dataIndex].positive ? RISK_META.HIGH.color : RISK_META.LOW.color,
        },
        data: sorted.map((i) => i.value),
      },
    ],
  };
}

/** Matrix heatmap (groups × categories) —— 适合密集二维对比，避免柱状图挤成一团。
 *  色阶默认固定 50–100（绝对分数档位），近似的值看起来就该近似；
 *  传 min/max 覆盖，或传 null 让色阶自适应数据范围。 */
export function buildHeatmap({ categories, series, min = 50, max = 100 }) {
  const yLabels = series.map((s) => s.name);
  const data = [];
  let dataMin = Infinity;
  let dataMax = -Infinity;
  series.forEach((s, y) =>
    (s.data || []).forEach((v, x) => {
      data.push([x, y, v]);
      if (v < dataMin) dataMin = v;
      if (v > dataMax) dataMax = v;
    })
  );
  if (!Number.isFinite(dataMin)) {
    dataMin = 0;
    dataMax = 100;
  }
  const vmMin = min == null ? Math.floor(dataMin) : min;
  const vmMax = max == null ? Math.ceil(dataMax) : max;
  const manyCols = categories.length > 6;
  return {
    tooltip: {
      ...baseTooltip(),
      position: 'top',
      formatter: (p) =>
        `${yLabels[p.value[1]]} · ${categories[p.value[0]]}<br/><b>${p.value[2]}</b>`,
    },
    grid: { left: 8, right: 16, top: 10, bottom: 56, containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      ...axisCommon(),
      axisLabel: { ...axisCommon().axisLabel, rotate: manyCols ? 32 : 0, interval: 0 },
    },
    yAxis: { type: 'category', data: yLabels, ...axisCommon(), splitLine: { show: false } },
    visualMap: {
      min: vmMin,
      max: vmMax,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 120,
      textStyle: { color: palette.textSecondary, fontSize: 11 },
      inRange: { color: [palette.riskHigh, palette.gold, palette.teal] },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: {
          show: true,
          color: '#fff',
          fontSize: 10,
          textBorderColor: 'rgba(0,0,0,0.55)',
          textBorderWidth: 2,
          formatter: (p) => p.value[2],
        },
        itemStyle: { borderColor: palette.bgDeep, borderWidth: 2, borderRadius: 4 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
      },
    ],
  };
}

/** Multi-series grouped bar chart */
export function buildGroupedBar({ categories, series }) {
  return {
    color: chartColors,
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    tooltip: { ...baseTooltip(), trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { color: palette.textSecondary }, icon: 'roundRect' },
    xAxis: { type: 'category', data: categories, ...axisCommon() },
    yAxis: { type: 'value', ...axisCommon() },
    series: series.map((s, idx) => ({
      name: s.name,
      type: 'bar',
      barGap: '20%',
      barWidth: '28%',
      itemStyle: {
        borderRadius: [5, 5, 0, 0],
        color: linearGradient(chartColors[idx % chartColors.length], `${chartColors[idx % chartColors.length]}22`),
      },
      data: s.data,
    })),
  };
}
