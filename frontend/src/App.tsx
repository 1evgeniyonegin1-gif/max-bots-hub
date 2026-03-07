import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { DashboardPage } from './pages/Dashboard';
import { BotsListPage } from './pages/BotsList';
import { CreateBotPage } from './pages/CreateBot';
import { BotDetailPage } from './pages/BotDetail';

function App() {
  const { isAuthenticated, isLoading, checkAuth } = useAuth();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-400 mt-4">Загрузка...</p>
        </div>
      </div>
    );
  }

  // Public routes
  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Protected routes
  return (
    <Routes>
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/bots" element={<BotsListPage />} />
      <Route path="/bots/new" element={<CreateBotPage />} />
      <Route path="/bots/:botId" element={<BotDetailPage />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
