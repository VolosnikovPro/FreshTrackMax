import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { SiteProvider } from './hooks/useSite';
import Layout from './components/common/Layout';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import ProtectedRoute from './routes/ProtectedRoute';
import { appRoutes } from './routes';
import { Loading } from './components/common/UI';

export default function App() {
  return (
    <AuthProvider>
      <SiteProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              {appRoutes.map(({ path, element: Page, allowedRoles }) => {
                const isIndex = path === '/';
                const el = (
                  <ProtectedRoute allowedRoles={allowedRoles}>
                    <Suspense fallback={<Loading />}><Page /></Suspense>
                  </ProtectedRoute>
                );
                return isIndex
                  ? <Route key={path} index element={el} />
                  : <Route key={path} path={path.slice(1)} element={el} />;
              })}
            </Route>
            <Route path="/404" element={<NotFoundPage />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </BrowserRouter>
      </SiteProvider>
    </AuthProvider>
  );
}