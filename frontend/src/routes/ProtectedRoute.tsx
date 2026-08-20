import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { UserRole } from '../types';
import LoadingPage from '../pages/LoadingPage';

interface Props { children: React.ReactNode; allowedRoles?: UserRole[]; }

export default function ProtectedRoute({ children, allowedRoles = [] }: Props) {
  const { loading, user } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingPage/>;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}