import { useEffect, useMemo, useState } from 'react';
import { Row, Col, Select, Button, Empty, Spin, Tag, Tooltip, message } from 'antd';
import {
  BookOutlined,
  ApartmentOutlined,
  TeamOutlined,
  AlertOutlined,
  ReloadOutlined,
  RightOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { PageHeader, KpiCard, ChartCard, Panel, RiskTag } from '../components/ui';
import { buildTrendChart, buildBarChart, buildRiskDonut } from '../theme/echarts';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [sections, setSections] = useState([]);
  const [sectionId, setSectionId] = useState(null);
  const [overview, setOverview] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [bootLoading, setBootLoading] = useState(true);
  const [panelLoading, setPanelLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.getDashboardSummary(), api.listSections()])
      .then(([sum, s]) => {
        setSummary(sum || null);
        setSections(s || []);
        if (s && s.length) setSectionId(s[0].id);
      })
      .catch(() => message.error('Failed to load dashboard'))
      .finally(() => setBootLoading(false));
  }, []);

  useEffect(() => {
    if (!sectionId) return;
    setPanelLoading(true);
    Promise.all([api.getOverview(sectionId), api.listPredictions(sectionId)])
      .then(([o, p]) => {
        setOverview(o);
        setPredictions(p || []);
      })
      .catch(() => message.error('Failed to load section overview'))
      .finally(() => setPanelLoading(false));
  }, [sectionId]);

  const highRisk = useMemo(
    () => predictions.filter((p) => p.risk_level === 'HIGH').sort((a, b) => b.probability - a.probability),
    [predictions]
  );

  const recalc = async () => {
    try {
      await api.recalculate(sectionId);
      message.success('Recalculation triggered');
      const o = await api.getOverview(sectionId);
      setOverview(o);
    } catch {
      message.error('Operation failed');
    }
  };

  if (bootLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  const risk = overview?.risk_summary;

  return (
    <div>
      <PageHeader
        title={`Command Center · Welcome, ${user?.full_name || user?.username}`}
        subtitle="Global teaching status and key risk alerts at a glance (sample data)"
        extra={
          sections.length > 0 && (
            <>
              <Select
                value={sectionId}
                onChange={setSectionId}
                style={{ minWidth: 220 }}
                options={sections.map((s) => ({
                  value: s.id,
                  label: `${s.course_code || 'Course'} · Section ${s.section_code}`,
                }))}
              />
              <Button icon={<ReloadOutlined />} onClick={recalc}>
                Recalculate
              </Button>
            </>
          )
        }
      />

      {/* KPI row — real DB-backed counts from /dashboard/summary */}
      <Row gutter={[16, 16]}>
        <Col xs={12} md={12} lg={6}>
          <KpiCard label="My courses" value={summary?.kpis?.course_count ?? '—'} icon={<BookOutlined />} color={palette.cyan} />
        </Col>
        <Col xs={12} md={12} lg={6}>
          <KpiCard label="Sections" value={summary?.kpis?.section_count ?? '—'} icon={<ApartmentOutlined />} color={palette.violet} />
        </Col>
        <Col xs={12} md={12} lg={6}>
          <KpiCard
            label="Students"
            value={summary?.kpis?.student_count ?? '—'}
            icon={<TeamOutlined />}
            color={palette.teal}
          />
        </Col>
        <Col xs={12} md={12} lg={6}>
          <KpiCard
            label="High-risk students"
            value={summary?.kpis?.high_risk_count ?? '—'}
            icon={<AlertOutlined />}
            color={palette.riskHigh}
            hint="Needs attention"
          />
        </Col>
      </Row>

      {sections.length === 0 ? (
        <Panel style={{ marginTop: 16 }}>
          <Empty
            description={
              <span style={{ color: palette.textSecondary }}>
                No sections yet. Create a course and section to start analyzing.
              </span>
            }
          >
            <Button type="primary" onClick={() => navigate('/courses')}>
              Create a course
            </Button>
          </Empty>
        </Panel>
      ) : (
        <Spin spinning={panelLoading}>
          {/* Trend + risk share */}
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={16}>
              <ChartCard
                title="Weekly average score trend"
                subtitle={overview ? `Last calculated: ${new Date(overview.last_calculated_at).toLocaleString('en-US')}` : ''}
                icon={<ThunderboltOutlined />}
                height={300}
                option={
                  overview
                    ? buildTrendChart({
                        categories: overview.trend.map((t) => `W${t.week}`),
                        values: overview.trend.map((t) => t.average),
                        name: 'Average',
                        min: 50,
                        max: 100,
                      })
                    : {}
                }
              />
            </Col>
            <Col xs={24} lg={8}>
              <ChartCard
                title="Risk distribution"
                icon={<AlertOutlined />}
                height={300}
                option={risk ? buildRiskDonut(risk) : {}}
              />
            </Col>
          </Row>

          {/* Distribution + high-risk watchlist */}
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={14}>
              <ChartCard
                title="Score distribution"
                icon={<ApartmentOutlined />}
                height={320}
                option={
                  overview
                    ? buildBarChart({
                        categories: overview.score_distribution.map((d) => d.range),
                        values: overview.score_distribution.map((d) => d.count),
                        name: 'Students',
                      })
                    : {}
                }
              />
            </Col>
            <Col xs={24} lg={10}>
              <Panel
                title="High-risk watchlist"
                icon={<AlertOutlined />}
                subtitle="Sorted by risk probability — click to view a student"
                extra={<Tag color="error">{highRisk.length}</Tag>}
                bodyStyle={{ padding: '6px 8px', maxHeight: 320, overflowY: 'auto' }}
              >
                {highRisk.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No high-risk students" />
                ) : (
                  highRisk.map((p) => (
                    <div
                      key={p.prediction_id}
                      onClick={() => navigate(`/sections/${sectionId}/students/${p.student_id}`)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '11px 12px',
                        borderRadius: 10,
                        cursor: 'pointer',
                        transition: 'background 0.2s',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(56,189,248,0.08)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ color: palette.textPrimary, fontWeight: 600, fontSize: 13 }}>
                          {p.anonymized_code}
                        </span>
                        <RiskTag level={p.risk_level} size="small" />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <Tooltip title="Risk probability">
                          <span style={{ color: palette.riskHigh, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                            {(p.probability * 100).toFixed(0)}%
                          </span>
                        </Tooltip>
                        <RightOutlined style={{ color: palette.textMuted, fontSize: 12 }} />
                      </div>
                    </div>
                  ))
                )}
              </Panel>
            </Col>
          </Row>

          {/* Section quick access */}
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            {sections.map((s) => (
              <Col xs={24} sm={12} lg={8} key={s.id}>
                <Panel hover bodyStyle={{ padding: 18 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>
                        {s.course_code} · Section {s.section_code}
                      </div>
                      <div style={{ color: palette.textSecondary, fontSize: 12, marginTop: 4 }}>
                        {s.course_name}
                      </div>
                    </div>
                    <Tag color={s.status === 'ACTIVE' ? 'green' : 'default'}>{s.status}</Tag>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
                    <Button size="small" type="primary" ghost onClick={() => navigate(`/sections/${s.id}/overview`)}>
                      Overview
                    </Button>
                    <Button size="small" onClick={() => navigate(`/sections/${s.id}/predictions`)}>
                      Prediction
                    </Button>
                    <Button size="small" onClick={() => navigate(`/sections/${s.id}/import`)}>
                      Import
                    </Button>
                  </div>
                </Panel>
              </Col>
            ))}
          </Row>
        </Spin>
      )}
    </div>
  );
}
