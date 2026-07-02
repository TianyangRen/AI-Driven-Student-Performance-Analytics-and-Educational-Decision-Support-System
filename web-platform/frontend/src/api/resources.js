import client from './client';

const unwrap = (r) => r.data?.data;

/* Courses / sections */
export const listCourses = () => client.get('/courses').then(unwrap);
export const createCourse = (payload) => client.post('/courses', payload).then(unwrap);
export const listSections = () => client.get('/sections').then(unwrap);
export const createSection = (payload) => client.post('/sections', payload).then(unwrap);

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

/* Comparisons / reports / imports */
export const runComparison = (payload) =>
  client.post('/analytics/comparisons', payload).then(unwrap);
export const createReport = (payload) => client.post('/reports', payload).then(unwrap);
export const createImport = (sectionId, formData) =>
  client
    .post(`/sections/${sectionId}/imports`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then(unwrap);
export const getImport = (batchId) => client.get(`/imports/${batchId}`).then(unwrap);
export const getImportErrors = (batchId) =>
  client.get(`/imports/${batchId}/errors`).then(unwrap);
