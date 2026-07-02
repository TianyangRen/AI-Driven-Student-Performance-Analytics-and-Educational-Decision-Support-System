import { useEffect, useMemo, useState } from 'react';
import { Row, Col, Table, Button, Segmented, Progress, Alert, message } from 'antd';
import {
  ThunderboltOutlined,
  ArrowLeftOutlined,
  AlertOutlined,
  WarningOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader, KpiCard, ChartCard, Panel, RiskTag } from '../components/ui';
import { buildRiskDonut } from '../theme/echarts';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

export default function Predictions() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');
  const [lastRun, setLastRun] = useState(null);

  const load = () => {
    setLoading(true);
    api
      .listPredictions(sectionId)
      .then((d) => setData(d || []))
      .catch(() => message.error('Failed to load predictions'))
      .finally(() => setLoading(false));
  };
  useEffect(load, [sectionId]);

  const run = async () => {
    setRunning(true);
    try {
      const res = await api.runPrediction(sectionId, { force: false });
      setLastRun(res);
      message.success('Prediction run completed');
      load();
    } catch {
      message.error('Prediction run failed');
    } finally {
      setRunning(false);
    }
  };

  const counts = useMemo(() => {
    const c = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    data.forEach((d) => {
      c[d.risk_level] = (c[d.risk_level] || 0) + 1;
    });
    return c;
  }, [data]);

  const filtered = useMemo(
    () => (filter === 'ALL' ? data : data.filter((d) => d.risk_level === filter)),
    [data, filter]
  );

  return (
    <div>
      <PageHeader
        title={`Risk Prediction · Section #${sectionId}`}
        subtitle="Student risk probability and level from the active model version (teaching aid only)"
        extra={
          <>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/sections/${sectionId}/overview`)}>
              Back to class
            </Button>
            <Button type="primary" icon={<ThunderboltOutlined />} loading={running} onClick={run}>
              Run prediction
            </Button>
          </>
        }
      />

      {lastRun && (
        <Alert
          type="success"
          showIcon
          style={{ marginBottom: 16, background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.3)' }}
          message={`Run #${lastRun.run_id} completed · model ${lastRun.model_version} · mode ${lastRun.ml_mode}`}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}>
          <KpiCard label="Predicted students" value={data.length} icon={<SafetyOutlined />} color={palette.cyan} />
        </Col>
        <Col xs={12} lg={6}>
          <KpiCard label="High risk" value={counts.HIGH} icon={<AlertOutlined />} color={palette.riskHigh} />
        </Col>
        <Col xs={12} lg={6}>
          <KpiCard label="Medium risk" value={counts.MEDIUM} icon={<WarningOutlined />} color={palette.riskMedium} />
        </Col>
        <Col xs={12} lg={6}>
          <KpiCard label="Low risk" value={counts.LOW} icon={<SafetyOutlined />} color={palette.riskLow} />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={8}>
          <ChartCard title="Risk distribution" icon={<AlertOutlined />} height={340} loading={loading}
            option={buildRiskDonut({ high: counts.HIGH, medium: counts.MEDIUM, low: counts.LOW })}
          />
        </Col>
        <Col xs={24} lg={16}>
          <Panel
            title="Prediction results"
            icon={<ThunderboltOutlined />}
            extra={
              <Segmented
                value={filter}
                onChange={setFilter}
                options={[
                  { label: 'All', value: 'ALL' },
                  { label: 'High', value: 'HIGH' },
                  { label: 'Medium', value: 'MEDIUM' },
                  { label: 'Low', value: 'LOW' },
                ]}
              />
            }
          >
            <Table
              className="cockpit-table"
              rowKey="prediction_id"
              dataSource={filtered}
              loading={loading}
              size="middle"
              pagination={{ pageSize: 7, showSizeChanger: false }}
              columns={[
                {
                  title: 'Student',
                  dataIndex: 'anonymized_code',
                  render: (v) => <span style={{ color: '#fff', fontWeight: 600 }}>{v}</span>,
                },
                {
                  title: 'Risk probability',
                  dataIndex: 'probability',
                  sorter: (a, b) => a.probability - b.probability,
                  defaultSortOrder: 'descend',
                  render: (v) => (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <Progress
                        percent={Math.round(v * 100)}
                        size="small"
                        showInfo={false}
                        strokeColor={v > 0.7 ? palette.riskHigh : v > 0.4 ? palette.riskMedium : palette.riskLow}
                        style={{ width: 90, marginBottom: 0 }}
                      />
                      <span style={{ color: palette.textPrimary, fontVariantNumeric: 'tabular-nums' }}>
                        {(v * 100).toFixed(1)}%
                      </span>
                    </div>
                  ),
                },
                {
                  title: 'Risk level',
                  dataIndex: 'risk_level',
                  render: (v) => <RiskTag level={v} />,
                },
                {
                  title: 'Action',
                  width: 110,
                  render: (_, r) => (
                    <Button type="link" size="small" onClick={() => navigate(`/sections/${sectionId}/students/${r.student_id}`)}>
                      Details
                    </Button>
                  ),
                },
              ]}
            />
          </Panel>
        </Col>
      </Row>
    </div>
  );
}
