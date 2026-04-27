import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { FiMail, FiLock } from 'react-icons/fi';
import { apiService } from '../services/api';
import { useLanguage } from '../contexts/LanguageContext';

interface LoginPageProps {
  setIsAuthenticated: (value: boolean) => void;
}

export default function LoginPage({ setIsAuthenticated }: LoginPageProps) {
  const { t } = useLanguage();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError(t('loginMissingFields'));
      return;
    }

    setLoading(true);
    try {
      await apiService.login(email, password);
      // 检查token是否成功保存
      if (apiService.isAuthenticated()) {
        setIsAuthenticated(true);
        navigate('/chat');
      } else {
        setError(t('loginAuthFailed'));
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || t('loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-center text-gray-900 mb-8">ChatAgent</h1>

        <form onSubmit={handleLogin} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('emailLabel')}
            </label>
            <div className="relative">
              <FiMail className="absolute left-3 top-3 text-gray-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t('emailPlaceholder')}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('passwordLabel')}
            </label>
            <div className="relative">
              <FiLock className="absolute left-3 top-3 text-gray-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t('passwordPlaceholder')}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition mt-6"
          >
            {loading ? t('signingIn') : t('signIn')}
          </button>
        </form>

        <p className="text-center text-gray-600 text-sm mt-6">
          {t('noAccount')}{' '}
          <Link to="/register" className="text-blue-500 hover:text-blue-700 font-semibold">
            {t('signUp')}
          </Link>
        </p>
      </div>
    </div>
  );
}
