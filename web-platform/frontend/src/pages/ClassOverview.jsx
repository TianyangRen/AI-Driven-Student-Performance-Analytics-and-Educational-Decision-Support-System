import { useEffect, useMemo, useState } from 'react';
import { Row, Col, Table, Button, Input, Segmented, Progress, message, Spin } from 'antd';
import {
  TeamOutlined,
  RiseOutlined,
  DashboardOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader, KpiCard, ChartCard, Panel, RiskTag } from '../components/ui';
import { buildBarChart, buildTrendChart, buildRiskDonut } from '../theme/echarts';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

export default function ClassOverview() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [keyword, setKeyword] = useState('');

  const load = () => {
    setLoading(true);
    Promise.all([api.getOverview(sectionId), api.getStudents(sectionId)])
      .then(([o, s]) => {
        setOverview(o);
        setStudents(s || []);
      })
      .catch(() => message.error('Failed to load'))
      .finally(() => setLoading(false));
  };
  useEffect(load, [sectionId]);

  const recalc = async () => {
    await api.recalculate(sectionId);
    message.success('Recalculation triggered');
    load();
  };

  const filtered = useMemo(() => {
    return students.filter(
      (s) =>
        (riskFilter === 'ALL' || s.risk_level === riskFilter) &&
        (!keyword || s.anonymized_code.toLowerCase().includes(keyword.toLowerCase()))
    );
  }, [students, riskFilter, keyword]);

  if (loading || !overview) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  const { kpis, risk_summary: risk } = overview;

  const columns = [
    {
      title: 'Student',
      dataIndex: 'anonymized_code',
      render: (v) => <span style={{ color: palette.textPrimary, fontWeight: 600 }}>{v}</span>,
    },
    {
      title: 'Average',
      dataIndex: 'average_score',
      sorter: (a, b) => a.average_score - b.average_score,
      render: (v) => (
        <span style={{ color: v < 60 ? palette.riskHigh : v < 75 ? palette.gold : palette.teal, fontWeight: 600 }}>
          {v}
        </span>
      ),
    },
    {
      title: 'Attendance',
      dataIndex: 'attendance_rate',
      sorter: (a, b) => a.attendance_rate - b.attendance_rate,
      render: (v) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Progress
            percent={Math.round(v * 100)}
            size="small"
            showInfo={false}
            strokeColor={v < 0.7 ? palette.riskHigh : palette.cyan}
            style={{ width: 80, marginBottom: 0 }}
          />
          <span style={{ color: palette.textSecondary, fontSize: 12 }}>{(v * 100).toFixed(0)}%</span>
        </div>
      ),
    },
    {
      title: 'Risk level',
      dataIndex: 'risk_level',
      filters: [
        { text: 'High', value: 'HIGH' },
        { text: 'Medium', value: 'MEDIUM' },
        { text: 'Low', value: 'LOW' },
      ],
      onFilter: (val, r) => r.risk_level === val,
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
  ];

  return (
    <div>
      <PageHeader
        title={`Class Overview · ${overview.section.course_code} · Section ${overview.section.section_code}`}
        subtitle={`Last calculated: ${new Date(overview.last_calculated_at).toLocaleString('en-US')}`}
        extra={
          <>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/sections')}>
              Back
            </Button>
            <Button type="primary" icon={<ReloadOutlined />} onClick={recalc}>
              Recalculate
            </Button>
          </>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}>
          <KpiCard label="Students" value={kpis.student_count} icon={<TeamOutlined />} color={palette.cyan} />
        </Col>
        <Col xs={12} lg={6}>
          <KpiCard label="Average score" value={kpis.average_score} icon={<RiseOutlined />} color={palette.violet} />
        </Col>
        <Col xs={12} lg={6}>
          <KpiCard label="Median" value={kpis.median_score} icon={<DashboardOutlined />} color={palette.teal} />
        </Col>
        <Col xs={12} lg={6}>
          <KpiCard
            label="Pass rate"
            value={(kpis.pass_rate * 100).toFixed(0)}
            suffix="%"
            icon={<CheckCircleOutlined />}
            color={palette.gold}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={9}>
          <ChartCard title="Score distribution" height={300}
            option={buildBarChart({
              categories: overview.score_distribution.map((d) => d.range),
              values: overview.score_distribution.map((d) => d.count),
              name: 'Students',
            })}
          />
        </Col>
        <Col xs={24} lg={9}>
          <ChartCard title="Weekly average trend" height={300}
            option={buildTrendChart({
              categories: overview.trend.map((t) => `W${t.week}`),
              values: overview.trend.map((t) => t.average),
              name: 'Average',
              min: 50,
              max: 100,
            })}
          />
        </Col>
        <Col xs={24} lg={6}>
          <ChartCard title="Risk distribution" height={300} option={buildRiskDonut(risk)} />
        </Col>
      </Row>

      <Panel
        title="Student performance"
        icon={<TeamOutlined />}
        style={{ marginTop: 16 }}
        extra={
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <Segmented
              value={riskFilter}
              onChange={setRiskFilter}
              options={[
                { label: 'All', value: 'ALL' },
                { label: 'High', value: 'HIGH' },
                { label: 'Medium', value: 'MEDIUM' },
                { label: 'Low', value: 'LOW' },
              ]}
            />
            <Input
              allowClear
              prefix={<SearchOutlined style={{ color: palette.textMuted }} />}
              placeholder="Search student code"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ width: 190 }}
            />
          </div>
        }
      >
        <Table
          className="cockpit-table"
          rowKey="student_id"
          dataSource={filtered}
          columns={columns}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          size="middle"
        />
      </Panel>
    </div>
  );
}
