import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bot, Plus, Settings, Trash2, Play, Pause } from 'lucide-react';
import { Layout } from '../components/Layout';
import { botsApi, type Bot as BotType } from '../api/client';

export function BotsListPage() {
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

  const handleDeploy = async (botId: string) => {
    try {
      await botsApi.deploy(botId);
      loadBots();
    } catch (error) {
      console.error('Failed to deploy bot:', error);
    }
  };

  const handleDelete = async (botId: string) => {
    if (!confirm('Вы уверены, что хотите удалить бота?')) return;

    try {
      await botsApi.delete(botId);
      loadBots();
    } catch (error) {
      console.error('Failed to delete bot:', error);
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      conversation: 'Диалоговый бот',
      content_generator: 'Контент-генератор',
    };
    return labels[type] || type;
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Мои боты</h1>
            <p className="text-slate-400 mt-1">Управление вашими ботами</p>
          </div>
          <Link to="/bots/new" className="btn btn-primary flex items-center gap-2">
            <Plus className="w-5 h-5" />
            <span>Создать бота</span>
          </Link>
        </div>

        {/* Bots Grid */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-slate-400 mt-4">Загрузка...</p>
          </div>
        ) : bots.length === 0 ? (
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
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {bots.map((bot) => (
              <BotCard
                key={bot.id}
                bot={bot}
                onDeploy={() => handleDeploy(bot.id)}
                onDelete={() => handleDelete(bot.id)}
                typeLabel={getTypeLabel(bot.bot_type)}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}

function BotCard({
  bot,
  onDeploy,
  onDelete,
  typeLabel,
}: {
  bot: BotType;
  onDeploy: () => void;
  onDelete: () => void;
  typeLabel: string;
}) {
  const statusColors = {
    ACTIVE: 'bg-green-500',
    DRAFT: 'bg-yellow-500',
    PAUSED: 'bg-blue-500',
    DELETED: 'bg-red-500',
  };

  const statusLabels = {
    ACTIVE: 'Активен',
    DRAFT: 'Черновик',
    PAUSED: 'Приостановлен',
    DELETED: 'Удалён',
  };

  return (
    <div className="card hover:border-slate-600 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white">{bot.bot_name}</h3>
            <p className="text-sm text-slate-400">{typeLabel}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              statusColors[bot.status as keyof typeof statusColors]
            }`}
          />
          <span className="text-xs text-slate-400">
            {statusLabels[bot.status as keyof typeof statusLabels]}
          </span>
        </div>
      </div>

      {bot.bot_username && (
        <p className="text-sm text-slate-400 mb-4">@{bot.bot_username}</p>
      )}

      <div className="flex items-center gap-2 pt-4 border-t border-slate-700">
        <Link
          to={`/bots/${bot.id}`}
          className="btn btn-secondary flex-1 flex items-center justify-center gap-2"
        >
          <Settings className="w-4 h-4" />
          <span>Настройки</span>
        </Link>

        {bot.status === 'DRAFT' && (
          <button
            onClick={onDeploy}
            className="btn btn-primary flex items-center gap-2"
            title="Активировать"
          >
            <Play className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={onDelete}
          className="btn btn-danger flex items-center gap-2"
          title="Удалить"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
