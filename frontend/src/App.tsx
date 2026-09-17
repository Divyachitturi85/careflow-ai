import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { VoiceAssistantPage } from './pages/patient/VoiceAssistantPage';
import { AppointmentsPage } from './pages/patient/AppointmentsPage';
import { QuestionnairePage } from './pages/patient/QuestionnairePage';
import { DoctorDashboard } from './pages/doctor/DoctorDashboard';
import { HospitalAdminDashboard } from './pages/hospital/HospitalAdminDashboard';
import { PlatformAdminDashboard } from './pages/admin/PlatformAdminDashboard';
import { LoginPage } from './pages/auth/LoginPage';

// Role-protected route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactElement; allowedRoles?: string[] }> = ({ 
  children, 
  allowedRoles 
}) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="h-8 w-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // If not authorized for this specific portal, navigate to their home
    if (user.role === 'DOCTOR') return <Navigate to="/doctor" replace />;
    if (user.role === 'HOSPITAL_ADMIN') return <Navigate to="/hospital" replace />;
    if (user.role === 'PLATFORM_ADMIN') return <Navigate to="/admin" replace />;
    return <Navigate to="/" replace />;
  }

  return children;
};

// Home router based on role
const HomeRoute: React.FC = () => {
  const { user } = useAuth();
  if (user?.role === 'DOCTOR') return <Navigate to="/doctor" replace />;
  if (user?.role === 'HOSPITAL_ADMIN') return <Navigate to="/hospital" replace />;
  if (user?.role === 'PLATFORM_ADMIN') return <Navigate to="/admin" replace />;
  return <VoiceAssistantPage />;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
          <Navbar />
          <main className="flex-1">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <HomeRoute />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/appointments"
                element={
                  <ProtectedRoute allowedRoles={['PATIENT', 'PLATFORM_ADMIN']}>
                    <AppointmentsPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/questionnaire"
                element={
                  <ProtectedRoute allowedRoles={['PATIENT', 'DOCTOR', 'PLATFORM_ADMIN']}>
                    <QuestionnairePage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/doctor"
                element={
                  <ProtectedRoute allowedRoles={['DOCTOR', 'HOSPITAL_ADMIN', 'PLATFORM_ADMIN']}>
                    <DoctorDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/hospital"
                element={
                  <ProtectedRoute allowedRoles={['HOSPITAL_ADMIN', 'PLATFORM_ADMIN']}>
                    <HospitalAdminDashboard />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin"
                element={
                  <ProtectedRoute allowedRoles={['PLATFORM_ADMIN']}>
                    <PlatformAdminDashboard />
                  </ProtectedRoute>
                }
              />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
