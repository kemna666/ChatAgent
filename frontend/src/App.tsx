import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { apiService } from './services/api';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ChatPage from './pages/ChatPage';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(apiService.isAuthenticated());

  useEffect(() => {
    const checkAuth = () => {
      setIsAuthenticated(apiService.isAuthenticated());
    };

    // 检查storage变化（token被保存或清除时触发）
    window.addEventListener('storage', checkAuth);
    
    // 也检查当前token状态（处理同标签页场景）
    checkAuth();
    
    return () => window.removeEventListener('storage', checkAuth);
  }, []);

  const handleLogout = () => {
    apiService.clearToken();
    setIsAuthenticated(false);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/chat" /> : <LoginPage setIsAuthenticated={setIsAuthenticated} />}
        />
        <Route
          path="/register"
          element={isAuthenticated ? <Navigate to="/chat" /> : <RegisterPage setIsAuthenticated={setIsAuthenticated} />}
        />
        <Route
          path="/chat"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <ChatPage onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to={isAuthenticated ? '/chat' : '/login'} />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
