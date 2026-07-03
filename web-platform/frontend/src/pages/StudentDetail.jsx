import { useEffect, useState } from 'react';
import { Row, Col, Table, Alert, Spin, Button, Statistic, Progress, message } from 'antd';
import {
  ArrowLeftOutlined,
  RadarChartOutlined,
  LineChartOutlined,
  BulbOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader, ChartCard, Panel, RiskTag } from '../components/ui';
import { buildRadarChart, buildTrendChart, buildContribBar } from '../theme/echarts';
import { palette, RISK_META } from '../theme/tokens';
import * as api from '../api/resources';

const INDICATOR_LABELS = {
  mastery: 'Mastery',
  stability: 'Stability',
  engagement: 'Engagement',
  improvement: 'Improvement',
};

export default function StudentDetail() {
  const { sectionId, studentId } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setExplanation(null);
    api
      .getStudentProfile(sectionId, studentId)
      .then((p) => {
        setProfile(p);
        // SHAP explanation exists only after a prediction run has produced a real
        // prediction_id for this student; skip gracefully otherwise.
        const predictionId = p?.risk?.prediction_id;
        if (predictionId) {
          api
            .getExplanation(predictionId)
            .then((e) => setExplanation(e))
            .catch(() => {});
        }
      })
      .catch(() => message.error('Failed to load student profile'))
      .finally(() => setLoading(false));
  }, [sectionId, studentId]);

  if (loading || !profile) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  const ind = profile.indicators;
  const riskMeta = RISK_META[profile.risk.level] || RISK_META.LOW;

  const radarOption = buildRadarChart({
    indicators: [
      { name: 'Mastery', max: 1 },
      { name: 'Stability', max: 1 },
      { name: 'Engagement', max: 1 },
      { name: 'Improvement', max: 0.5, min: -0.3 },
    ],
    values: [ind.mastery, ind.stability, ind.engagement, ind.improvement],
  });

  const trendOption = buildTrendChart({
    categories: profile.trend.map((t) => `W${t.week}`),
    values: profile.trend.map((t) => t.score),
    name: 'Score',
    color: palette.violet,
  });

  return (
    <div>
      <PageHeader
        title={`Student Detail · ${profile.student.anonymized_code}`}
        subtitle="Multi-dimensional profile, score trend and AI risk explanation"
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/sections/${sectionId}/overview`)}>
            Back to class
          </Button>
        }
      />

      {/* Overview row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Panel hover bodyStyle={{ padding: 22, position: 'relative', overflow: 'hidden' }}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: `radial-gradient(220px 120px at 90% 0%, ${riskMeta.color}22, transparent)`,
              }}
            />
            <div style={{ position: 'relative' }}>
              <div style={{ color: palette.textSecondary, fontSize: 13 }}>Overall risk assessment</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 14 }}>
                <Progress
                  type="dashboard"
                  percent={Math.round(profile.risk.probability * 100)}
                  size={110}
                  strokeColor={riskMeta.color}
                  format={(p) => (
                    <span style={{ color: '#fff', fontSize: 22, fontWeight: 700 }}>{p}%</span>
                  )}
                />
                <div>
                  <RiskTag level={profile.risk.level} />
                  <div style={{ color: palette.textMuted, fontSize: 12, marginTop: 10, maxWidth: 150 }}>
                    Higher probability suggests earlier instructor outreach.
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </Col>
        <Col xs={24} lg={16}>
          <Panel title="Multi-dimensional indicators" icon={<ExperimentOutlined />} bodyStyle={{ padding: 18 }}>
            <Row gutter={[12, 12]}>
              {Object.entries(ind).map(([key, val]) => (
                <Col xs={12} sm={6} key={key}>
                  <div
                    style={{
                      padding: '14px 16px',
                      borderRadius: 12,
                      background: 'rgba(10,19,48,0.45)',
                      border: '1px solid rgba(94,124,196,0.16)',
                    }}
                  >
                    <Statistic
                      title={<span style={{ color: palette.textSecondary }}>{INDICATOR_LABELS[key]}</span>}
                      value={val}
                      precision={2}
                      valueStyle={{ color: '#fff', fontSize: 24 }}
                    />
                    <Progress
                      percent={Math.max(0, Math.min(100, Math.round(((val + (key === 'improvement' ? 0.3 : 0)) / (key === 'improvement' ? 0.8 : 1)) * 100)))}
                      showInfo={false}
                      size="small"
                      strokeColor={palette.cyan}
                      style={{ marginBottom: 0, marginTop: 4 }}
                    />
                  </div>
                </Col>
              ))}
            </Row>
          </Panel>
        </Col>
      </Row>

      {/* Radar + trend */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={10}>
          <ChartCard title="Ability radar" icon={<RadarChartOutlined />} height={320} option={radarOption} />
        </Col>
        <Col xs={24} lg={14}>
          <ChartCard title="Weekly score trend" icon={<LineChartOutlined />} height={320} option={trendOption} />
        </Col>
      </Row>

      {/* Assessment details */}
      <Panel title="Assessment details" style={{ marginTop: 16 }}>
        <Table
          className="cockpit-table"
          rowKey="name"
          dataSource={profile.assessments}
          pagination={false}
          size="middle"
          columns={[
            { title: 'Assessment', dataIndex: 'name', render: (v) => <span style={{ color: '#fff' }}>{v}</span> },
            { title: 'Type', dataIndex: 'type', render: (v) => <span style={{ color: palette.textSecondary }}>{v}</span> },
            {
              title: 'Score',
              dataIndex: 'score',
              render: (v) => (
                <span style={{ color: v < 60 ? palette.riskHigh : palette.teal, fontWeight: 600 }}>{v}</span>
              ),
            },
            { title: 'Weight (%)', dataIndex: 'weight' },
          ]}
        />
      </Panel>

      {/* SHAP explanation */}
      {explanation && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={14}>
            <ChartCard
              title="Risk factors (SHAP)"
              icon={<BulbOutlined />}
              subtitle="Positive (red) raises risk, negative (cyan) lowers risk"
              height={280}
              option={buildContribBar({
                items: explanation.top_factors.map((f) => ({
                  name: f.display_name,
                  value: f.contribution,
                  positive: f.direction === 'increase_risk',
                })),
              })}
            />
          </Col>
          <Col xs={24} lg={10}>
            <Panel title="AI suggestion" icon={<BulbOutlined />} style={{ height: '100%' }}>
              <Alert
                type="warning"
                showIcon
                message={explanation.disclaimer}
                style={{ marginBottom: 16, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.3)' }}
              />
              <div
                style={{
                  padding: 16,
                  borderRadius: 12,
                  background: 'rgba(56,189,248,0.07)',
                  border: '1px solid rgba(56,189,248,0.2)',
                  color: palette.textPrimary,
                  lineHeight: 1.8,
                }}
              >
                {explanation.suggestion}
              </div>
              <div style={{ marginTop: 14, color: palette.textMuted, fontSize: 12 }}>
                Model version: {explanation.model_version}
              </div>
            </Panel>
          </Col>
        </Row>
      )}
    </div>
  );
}
