import client from './client';

const unwrap = (r) => r.data?.data;

/* Courses / sections */
export const listCourses = () => client.get('/courses').then(unwrap);
export const createCourse = (payload) => client.post('/courses', payload).then(unwrap);
export const updateCourse = (id, payload) => client.patch(`/courses/${id}`, payload).then(unwrap);
export const listSections = () => client.get('/sections').then(unwrap);
export const createSection = (payload) => client.post('/sections', payload).then(unwrap);
export const updateSection = (id, payload) => client.patch(`/sections/${id}`, payload).then(unwrap);

/* Dashboard (real DB-backed summary) */
export const getDashboardSummary = () => client.get('/dashboard/summary').then(unwrap);

/* Class analytics */
export const getOverview = (sectionId) =>
  client.get(`/sections/${sectionId}/overview`).then(unwrap);
export const getStudents = (sectionId) =>
  client.get(`/sections/${sectionId}/students`).then(unwrap);
export const recalculate = (sectionId) =>
  client.post(`/sections/${sectionId}/analytics/recalculate`).then(unwrap);

/* Student analytics */
export const getStudentProfile = (sectionId, studentId) =>
  client.get(`/sections/${sectionId}/students/${studentId}/profile`).then(unwrap);

/* Predictions & explanations */
export const runPrediction = (sectionId, body = {}) =>
  client.post(`/sections/${sectionId}/predictions/run`, body).then(unwrap);
export const listPredictions = (sectionId) =>
  client.get(`/sections/${sectionId}/predictions`).then(unwrap);
export const getExplanation = (predictionId) =>
  client.get(`/predictions/${predictionId}/explanation`).then(unwrap);

/* Cohort insights —— 透传 ML 服务对固定研究数据集的分析（结课复盘 / 预警 / 测评质量） */
export const getCohortProfile = () => client.get('/analytics/cohort-profile').then(unwrap);
export const getWarningTimeline = () => client.get('/analytics/warning-timeline').then(unwrap);
export const getAssessmentQuality = () => client.get('/analytics/assessment-quality').then(unwrap);

/* Comparisons / reports / imports */
export const runComparison = (payload) =>
  client.post('/analytics/comparisons', payload).then(unwrap);
export const createReport = (payload) => client.post('/reports', payload).then(unwrap);
// 下载走带鉴权的 axios（window.open 不会带 Token 头，会 401）
export const downloadReport = (id) =>
  client.get(`/reports/${id}/download`, { responseType: 'blob' });
export const createImport = (sectionId, formData) =>
  client
    .post(`/sections/${sectionId}/imports`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then(unwrap);
export const getImport = (batchId) => client.get(`/imports/${batchId}`).then(unwrap);
export const getImportErrors = (batchId) =>
  client.get(`/imports/${batchId}/errors`).then(unwrap);
