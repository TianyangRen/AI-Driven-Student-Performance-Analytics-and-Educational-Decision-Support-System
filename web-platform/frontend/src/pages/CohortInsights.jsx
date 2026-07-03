import { useEffect, useState } from 'react';
import { Tabs, Table, Tag, Alert, Row, Col, Spin, Empty, List, Statistic } from 'antd';
import {
  ClusterOutlined,
  AlertOutlined,
  ExperimentOutlined,
  WarningOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { PageHeader, Panel, KpiCard, ChartCard, RiskTag } from '../components/ui';
import { buildTrendChart } from '../theme/echarts';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

const stripOffering = (o) => String(o || '').replace('Data-', '');
const up = (v) => String(v || 'low').toUpperCase();

const VERDICT_COLOR = {
  'good discriminator': 'green',
  weak: 'gold',
  poor: 'red',
  ceiling: 'volcano',
  'no variance': 'red',
  'n/a': 'default',
};

/** Small hook: fetch one endpoint, expose {data, loading, error}. */
function useEndpoint(fetchFn) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  useEffect(() => {
    let alive = true;
    fetchFn()
      .then((d) => alive && setState({ data: d, loading: false, error: null }))
      .catch((e) => {
        const msg =
          e?.response?.data?.error?.message ||
          e?.response?.data?.detail ||
          'The ML service is unavailable. Start the backend on :8000 and retry.';
        alive && setState({ data: null, loading: false, error: msg });
      });
    return () => {
      alive = false;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return state;
}

function Loader({ loading, error, children }) {
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }
  if (error) {
    return (
      <Alert
        type="warning"
        showIcon
        message="Cohort analytics unavailable"
        description={error}
        style={{ marginTop: 8 }}
      />
    );
  }
  return children;
}

/* ------------------------------------------------------------------ */
/* Tab 1 — Cohort Profile                                             */
/* ------------------------------------------------------------------ */
function CohortProfileTab() {
  const { data, loading, error } = useEndpoint(api.getCohortProfile);
  return (
    <Loader loading={loading} error={error}>
      {data && <CohortProfileBody d={data} />}
    </Loader>
  );
}

function CohortProfileBody({ d }) {
  const cs = d.class_stats || {};
  const memberCols = [
    { title: 'Student', dataIndex: 'id', render: (v, r) => (
      <span style={{ color: '#fff' }}>{v} <span style={{ color: palette.textMuted, fontSize: 11 }}>({stripOffering(r.offering)})</span></span>
    ) },
    { title: 'Pctl', dataIndex: 'pctl', width: 70, render: (v) => (v ?? '--') },
    { title: 'Proj.', dataIndex: 'projected', width: 70 },
    { title: 'Risk', dataIndex: 'risk', width: 90, render: (v) => <RiskTag level={up(v)} /> },
  ];

  return (
    <div>
      {d.meta?.data_basis && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message="Retrospective view" description={d.meta.data_basis} />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={12} lg={5}><KpiCard label="Students" value={cs.n} color={palette.cyan} /></Col>
        <Col xs={12} lg={5}><KpiCard label="Projected mean" value={cs.projected_mean} color={palette.violet} /></Col>
        <Col xs={12} lg={5}><KpiCard label="Score spread (CV%)" value={cs.cv_pct} suffix="%" color={palette.teal} /></Col>
        <Col xs={12} lg={5}><KpiCard label="At risk" value={cs.pct_at_risk} suffix="%" color={palette.gold} /></Col>
        <Col xs={24} lg={4}><KpiCard label="Disengaged" value={cs.n_disengaged} color={palette.riskHigh} /></Col>
      </Row>

      <Panel title="Weakness boards" icon={<ClusterOutlined />} style={{ marginTop: 16 }}
        extra={<span style={{ color: palette.textMuted, fontSize: 12 }}>bottom-quartile per dimension · students overlap across boards</span>}>
        <Row gutter={[16, 16]}>
          {(d.weakness_boards || []).map((b) => (
            <Col xs={24} lg={12} xxl={6} key={b.dim}>
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: '#fff', fontWeight: 600 }}>{b.dim}</span>
                <span style={{ color: palette.textSecondary, fontSize: 12, marginLeft: 8 }}>
                  {b.n} students · {b.share_pct}%
                </span>
              </div>
              <Table
                className="cockpit-table" rowKey={(r) => `${r.id}-${r.offering}`}
                dataSource={b.members} columns={memberCols}
                size="small" pagination={{ pageSize: 5, showSizeChanger: false, simple: true }}
              />
            </Col>
          ))}
        </Row>
      </Panel>

      <Panel title="Disengagement track" icon={<WarningOutlined />} style={{ marginTop: 16 }}
        extra={<span style={{ color: palette.textMuted, fontSize: 12 }}>{d.disengagement?.rule}</span>}>
        <Table
          className="cockpit-table" rowKey={(r) => `${r.id}-${r.offering}`}
          dataSource={d.disengagement?.members || []}
          size="middle" pagination={{ pageSize: 8 }}
          columns={[
            { title: 'Student', dataIndex: 'id', render: (v, r) => <span style={{ color: '#fff' }}>{v} <span style={{ color: palette.textMuted, fontSize: 11 }}>({stripOffering(r.offering)})</span></span> },
            { title: 'Tag', dataIndex: 'tag', render: (v) => <Tag color={v === 'disengaged' ? 'red' : 'gold'}>{v}</Tag> },
            { title: 'Missed (total/late)', render: (_, r) => `${r.missed_total} / ${r.missed_late}` },
            { title: 'Projected', dataIndex: 'projected' },
            { title: 'Final', dataIndex: 'final' },
            { title: 'Risk', dataIndex: 'risk', render: (v) => <RiskTag level={up(v)} /> },
          ]}
        />
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tab 2 — Early Warning                                              */
/* ------------------------------------------------------------------ */
function WarningTimelineTab() {
  const { data, loading, error } = useEndpoint(api.getWarningTimeline);
  return (
    <Loader loading={loading} error={error}>
      {data && <WarningTimelineBody d={data} />}
    </Loader>
  );
}

function WarningTimelineBody({ d }) {
  const curve = d.curve || [];
  const sc = d.sanity_check || {};
  return (
    <div>
      {d.meta?.alert_rule && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message="Mid-semester early-warning view"
          description={`${d.meta.assumption || ''} · alert = ${d.meta.alert_rule}`} />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <ChartCard title="Prediction accuracy by week (MAE ↓ better)" icon={<AlertOutlined />} height={300}
            option={buildTrendChart({
              categories: curve.map((c) => `${c.snapshot} (w${c.approx_week})`),
              values: curve.map((c) => c.mae),
              name: 'MAE', color: palette.gold, min: 0,
            })} />
        </Col>
        <Col xs={24} lg={10}>
          <Panel title="Alert effectiveness" icon={<BulbOutlined />} style={{ height: '100%' }}>
            <Row gutter={[12, 12]}>
              <Col span={8}><Statistic title={<span style={{ color: palette.textSecondary }}>Declining</span>} value={sc.n_declining ?? '--'} valueStyle={{ color: palette.riskHigh }} /></Col>
              <Col span={8}><Statistic title={<span style={{ color: palette.textSecondary }}>Declining final</span>} value={sc.declining_mean_final ?? '--'} valueStyle={{ color: palette.gold }} /></Col>
              <Col span={8}><Statistic title={<span style={{ color: palette.textSecondary }}>Stable final</span>} value={sc.stable_mean_final ?? '--'} valueStyle={{ color: palette.teal }} /></Col>
            </Row>
            <Table
              className="cockpit-table" style={{ marginTop: 14 }} rowKey="snapshot"
              dataSource={curve} size="small" pagination={false}
              columns={[
                { title: 'Snapshot', dataIndex: 'snapshot' },
                { title: 'Week', dataIndex: 'approx_week' },
                { title: 'MAE', dataIndex: 'mae' },
                { title: 'R²', dataIndex: 'r2' },
              ]}
            />
          </Panel>
        </Col>
      </Row>

      <Panel title="Declining students (drop ≥ 5 pts)" icon={<WarningOutlined />} style={{ marginTop: 16 }}>
        <Table
          className="cockpit-table" rowKey={(r) => `${r.id}-${r.offering}`}
          dataSource={d.declining || []} size="middle" pagination={{ pageSize: 8 }}
          columns={[
            { title: 'Student', dataIndex: 'id', render: (v, r) => <span style={{ color: '#fff' }}>{v} <span style={{ color: palette.textMuted, fontSize: 11 }}>({stripOffering(r.offering)})</span></span> },
            { title: 'W3', render: (_, r) => r.preds?.W3 ?? '--' },
            { title: 'W6', render: (_, r) => r.preds?.W6 ?? '--' },
            { title: 'W9', render: (_, r) => r.preds?.W9 ?? '--' },
            { title: 'W12', render: (_, r) => r.preds?.W12 ?? '--' },
            { title: 'Max drop', dataIndex: 'max_drop', render: (v) => <span style={{ color: palette.riskHigh, fontWeight: 600 }}>{v}</span> },
            { title: 'Final', dataIndex: 'final' },
          ]}
        />
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tab 3 — Assessment Quality                                         */
/* ------------------------------------------------------------------ */
function AssessmentQualityTab() {
  const { data, loading, error } = useEndpoint(api.getAssessmentQuality);
  return (
    <Loader loading={loading} error={error}>
      {data && <AssessmentQualityBody d={data} />}
    </Loader>
  );
}

function AssessmentQualityBody({ d }) {
  return (
    <div>
      {d.meta?.caveat && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message="CTT item analysis" description={d.meta.caveat} />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Panel title="Auto insights" icon={<BulbOutlined />} style={{ height: '100%' }}>
            <List
              dataSource={d.insights || []}
              renderItem={(item) => (
                <List.Item style={{ borderBlockEnd: '1px solid rgba(94,124,196,0.12)' }}>
                  <span style={{ color: palette.textPrimary }}>{item}</span>
                </List.Item>
              )}
            />
          </Panel>
        </Col>
        <Col xs={24} lg={16}>
          <Panel title="Category summary" icon={<ExperimentOutlined />} style={{ height: '100%' }}>
            <Table
              className="cockpit-table" rowKey="category"
              dataSource={d.category_summary || []} size="middle" pagination={false}
              columns={[
                { title: 'Category', dataIndex: 'category', render: (v) => <span style={{ color: '#fff', textTransform: 'capitalize' }}>{v}</span> },
                { title: 'Avg discrimination (r)', dataIndex: 'avg_discrimination_r', render: (v) => (v ?? '--') },
                { title: 'Avg ceiling (%)', dataIndex: 'avg_ceiling_pct', render: (v) => (v ?? '--') },
              ]}
            />
          </Panel>
        </Col>
      </Row>

      <Panel title="Assessment components" icon={<ExperimentOutlined />} style={{ marginTop: 16 }}>
        <Table
          className="cockpit-table" rowKey="label"
          dataSource={d.components || []} size="middle" pagination={{ pageSize: 12 }}
          columns={[
            { title: 'Component', dataIndex: 'label', render: (v) => <span style={{ color: '#fff' }}>{v}</span> },
            { title: 'Category', dataIndex: 'category', render: (v) => <span style={{ color: palette.textSecondary, textTransform: 'capitalize' }}>{v}</span> },
            { title: 'Difficulty (%)', dataIndex: 'difficulty_pct', sorter: (a, b) => a.difficulty_pct - b.difficulty_pct },
            { title: 'Discrimination (r)', dataIndex: 'discrimination_r', sorter: (a, b) => (a.discrimination_r ?? -9) - (b.discrimination_r ?? -9), render: (v) => (v == null ? '--' : v) },
            { title: 'Ceiling (%)', dataIndex: 'ceiling_pct' },
            { title: 'Verdict', dataIndex: 'verdict', render: (v) => <Tag color={VERDICT_COLOR[v] || 'default'}>{v}</Tag> },
          ]}
        />
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
export default function CohortInsights() {
  return (
    <div>
      <PageHeader
        title="Cohort Insights"
        subtitle="Whole-cohort analytics from the ML research dataset — retrospective profile, early-warning timeline, and assessment quality"
      />
      <Tabs
        defaultActiveKey="profile"
        items={[
          { key: 'profile', label: (<span><ClusterOutlined /> Cohort profile</span>), children: <CohortProfileTab /> },
          { key: 'warning', label: (<span><AlertOutlined /> Early warning</span>), children: <WarningTimelineTab /> },
          { key: 'quality', label: (<span><ExperimentOutlined /> Assessment quality</span>), children: <AssessmentQualityTab /> },
        ]}
      />
    </div>
  );
}
