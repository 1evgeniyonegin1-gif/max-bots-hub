import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bot, MessageSquare, Plus, Zap } from 'lucide-react';
import { Layout } from '../components/Layout';
import { botsApi, type Bot as BotType } from '../api/client';
import { useAuth } from '../hooks/useAuth';

export function DashboardPage() {
  const { user } = useAuth();
  const [bots, setBots] = useState<BotType[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadBots();
  }, []);

  const loadBots = async () => {
    try {
      const data = await botsApi.list();
      setBots(data.bots || []);
    } catch (error) {
      console.error('Failed to load bots:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const activeBots = bots.filter((b) => b.status === 'ACTIVE');
  const draftBots = bots.filter((b) => b.status === 'DRAFT');

  return (
    <Layout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">
            Привет, {user?.name || 'User'}!
          </h1>
          <p className="text-slate-400 mt-2">
            Добро пожаловать в MAX BOTS HUB
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            icon={Bot}
            label="Всего ботов"
            value={bots.length}
            color="blue"
          />
          <StatCard
            icon={Zap}
            label="Активных"
            value={activeBots.length}
            color="green"
          />
          <StatCard
            icon={MessageSquare}
            label="Черновиков"
            value={draftBots.length}
            color="yellow"
          />
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h2 className="text-xl font-semibold text-white mb-4">Быстрые действия</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link
              to="/bots/new"
              className="flex items-center gap-4 p-4 bg-slate-700 rounded-lg hover:bg-slate-600 transition-colors"
            >
              <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center">
                <Plus className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-medium text-white">Создать бота</h3>
                <p className="text-sm text-slate-400">Выберите шаблон и настройте</p>
              </div>
            </Link>

            <Link
              to="/bots"
              className="flex items-center gap-4 p-4 bg-slate-700 rounded-lg hover:bg-slate-600 transition-colors"
            >
              <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h3 className="font-medium text-white">Мои боты</h3>
                <p className="text-sm text-slate-400">Управление существующими</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent Bots */}
        {bots.length > 0 && (
          <div className="card">
            <h2 className="text-xl font-semibold text-white mb-4">Последние боты</h2>
            <div className="space-y-3">
              {bots.slice(0, 5).map((bot) => (
                <Link
                  key={bot.id}
                  to={`/bots/${bot.id}`}
                  className="flex items-center justify-between p-4 bg-slate-700 rounded-lg hover:bg-slate-600 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Bot className="w-5 h-5 text-slate-400" />
                    <div>
                      <h3 className="font-medium text-white">{bot.bot_name}</h3>
                      <p className="text-sm text-slate-400">{bot.bot_type}</p>
                    </div>
                  </div>
                  <StatusBadge status={bot.status} />
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && bots.length === 0 && (
          <div className="card text-center py-12">
            <Bot className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">
              У вас пока нет ботов
            </h3>
            <p className="text-slate-400 mb-6">
              Создайте своего первого бота за пару минут
            </p>
            <Link to="/bots/new" className="btn btn-primary">
              Создать бота
            </Link>
          </div>
        )}
      </div>
    </Layout>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: 'blue' | 'green' | 'yellow';
}) {
  const colors = {
    blue: 'bg-blue-900/50 border-blue-800',
    green: 'bg-green-900/50 border-green-800',
    yellow: 'bg-yellow-900/50 border-yellow-800',
  };

  const iconColors = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    yellow: 'text-yellow-400',
  };

  return (
    <div className={`card ${colors[color]} border`}>
      <div className="flex items-center gap-4">
        <Icon className={`w-8 h-8 ${iconColors[color]}`} />
        <div>
          <p className="text-2xl font-bold text-white">{value}</p>
          <p className="text-sm text-slate-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles = {
    ACTIVE: 'badge-success',
    DRAFT: 'badge-warning',
    PAUSED: 'badge-info',
    DELETED: 'badge-danger',
  };

  const labels = {
    ACTIVE: 'Активен',
    DRAFT: 'Черновик',
    PAUSED: 'Приостановлен',
    DELETED: 'Удалён',
  };

  return (
    <span className={`badge ${styles[status as keyof typeof styles] || 'badge-info'}`}>
      {labels[status as keyof typeof labels] || status}
    </span>
  );
}
