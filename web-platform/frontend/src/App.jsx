import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Courses from './pages/Courses.jsx';
import Sections from './pages/Sections.jsx';
import ImportData from './pages/ImportData.jsx';
import ClassOverview from './pages/ClassOverview.jsx';
import StudentDetail from './pages/StudentDetail.jsx';
import Predictions from './pages/Predictions.jsx';
import Comparisons from './pages/Comparisons.jsx';
import Reports from './pages/Reports.jsx';
import Profile from './pages/Profile.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="courses" element={<Courses />} />
        <Route path="sections" element={<Sections />} />
        <Route path="sections/:sectionId/import" element={<ImportData />} />
        <Route path="sections/:sectionId/overview" element={<ClassOverview />} />
        <Route path="sections/:sectionId/students/:studentId" element={<StudentDetail />} />
        <Route path="sections/:sectionId/predictions" element={<Predictions />} />
        <Route path="comparisons" element={<Comparisons />} />
        <Route path="reports" element={<Reports />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
