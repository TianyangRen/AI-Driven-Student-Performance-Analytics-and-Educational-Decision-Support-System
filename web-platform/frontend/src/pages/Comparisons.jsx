import { useState } from 'react';
import { Button, Select, Empty, message } from 'antd';
import { BarChartOutlined, SwapOutlined } from '@ant-design/icons';
import { PageHeader, Panel, ChartCard } from '../components/ui';
import { buildGroupedBar } from '../theme/echarts';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

const DIMENSIONS = [
  { value: 'SECTION', label: 'By section' },
  { value: 'COURSE', label: 'By course' },
  { value: 'TERM', label: 'By term' },
  { value: 'ASSESSMENT_TYPE', label: 'By assessment type' },
];

export default function Comparisons() {
  const [dimension, setDimension] = useState('SECTION');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const onRun = async () => {
    setLoading(true);
    try {
      const data = await api.runComparison({ dimension });
      setResult(data);
    } catch {
      message.error('Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Comparisons"
        subtitle="Cohort performance comparison across sections / courses / terms / assessment types"
        extra={
          <>
            <Select value={dimension} onChange={setDimension} style={{ width: 200 }} options={DIMENSIONS} />
            <Button type="primary" icon={<SwapOutlined />} loading={loading} onClick={onRun}>
              Generate
            </Button>
          </>
        }
      />

      {result ? (
        <ChartCard
          title="Comparison result"
          icon={<BarChartOutlined />}
          subtitle={`Dimension: ${DIMENSIONS.find((d) => d.value === dimension)?.label}`}
          height={420}
          loading={loading}
          option={buildGroupedBar({ categories: result.labels, series: result.series })}
        />
      ) : (
        <Panel bodyStyle={{ padding: 60 }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span style={{ color: palette.textSecondary }}>
                Choose a dimension and click “Generate” to view results
              </span>
            }
          />
        </Panel>
      )}
    </div>
  );
}
