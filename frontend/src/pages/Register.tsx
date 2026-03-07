import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bot, Loader2 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await register(name, email);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации. Попробуйте ещё раз.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Bot className="w-16 h-16 text-primary-500" />
          </div>
          <h1 className="text-3xl font-bold text-white">MAX BOTS HUB</h1>
          <p className="text-slate-400 mt-2">Создайте аккаунт</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-4 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-slate-300 mb-2">
                Имя / Название компании
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                placeholder="Иван Иванов"
                required
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="your@email.com"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Регистрация...</span>
                </>
              ) : (
                <span>Зарегистрироваться</span>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-slate-400">
              Уже есть аккаунт?{' '}
              <Link to="/login" className="text-primary-400 hover:text-primary-300">
                Войти
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
