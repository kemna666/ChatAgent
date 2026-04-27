import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { apiService } from '../services/api';

interface ProtectedRouteProps {
  isAuthenticated: boolean;
  children: ReactNode;
}

export default function ProtectedRoute({ isAuthenticated, children }: ProtectedRouteProps) {
  // 同时检查prop和实际的token状态，确保auth检查准确
  const actuallyAuthenticated = apiService.isAuthenticated();
  
  if (!actuallyAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
