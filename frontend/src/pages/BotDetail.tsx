import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Bot, Play, Pause, Trash2, Save, Loader2, Copy, Check } from 'lucide-react';
import { Layout } from '../components/Layout';
import { botsApi, type Bot as BotType, type BotTemplate } from '../api/client';

export function BotDetailPage() {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [bot, setBot] = useState<BotType | null>(null);
  const [templates, setTemplates] = useState<Record<string, BotTemplate>>({});
  const [config, setConfig] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadData();
  }, [botId]);

  const loadData = async () => {
    if (!botId) return;

    try {
      const [botData, templatesData] = await Promise.all([
        botsApi.get(botId),
        botsApi.getTemplates(),
      ]);
      setBot(botData);
      setConfig(botData.config || {});
      setTemplates(templatesData.templates || {});
    } catch (error) {
      console.error('Failed to load bot:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!botId) return;

    setIsSaving(true);
    try {
      await botsApi.updateConfig(botId, config);
      loadData();
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeploy = async () => {
    if (!botId) return;

    try {
      await botsApi.deploy(botId);
      loadData();
    } catch (error) {
      console.error('Failed to deploy:', error);
    }
  };

  const handleDelete = async () => {
    if (!botId) return;
    if (!confirm('Вы уверены, что хотите удалить бота?')) return;

    try {
      await botsApi.delete(botId);
      navigate('/bots');
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  const copyToken = () => {
    if (bot?.bot_token) {
      navigator.clipboard.writeText(bot.bot_token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      </Layout>
    );
  }

  if (!bot) {
    return (
      <Layout>
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-white">Бот не найден</h2>
          <button onClick={() => navigate('/bots')} className="btn btn-primary mt-4">
            Вернуться к списку
          </button>
        </div>
      </Layout>
    );
  }

  const template = templates[bot.bot_type];

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/bots')}
            className="p-2 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-white">{bot.bot_name}</h1>
            <p className="text-slate-400 mt-1">{template?.name || bot.bot_type}</p>
          </div>
          <StatusBadge status={bot.status} />
        </div>

        {/* Info */}
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Информация</h2>

          <div className="space-y-4">
            {bot.bot_username && (
              <div className="flex items-center justify-between py-3 border-b border-slate-700">
                <span className="text-slate-400">Username</span>
                <span className="text-white">@{bot.bot_username}</span>
              </div>
            )}

            {bot.bot_token && (
              <div className="flex items-center justify-between py-3 border-b border-slate-700">
                <span className="text-slate-400">Token</span>
                <div className="flex items-center gap-2">
                  <code className="text-xs text-slate-300 bg-slate-700 px-2 py-1 rounded">
                    {bot.bot_token.slice(0, 10)}...
                  </code>
                  <button
                    onClick={copyToken}
                    className="p-1 text-slate-400 hover:text-white transition-colors"
                    title="Копировать"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-green-400" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between py-3 border-b border-slate-700">
              <span className="text-slate-400">Создан</span>
              <span className="text-white">
                {new Date(bot.created_at).toLocaleDateString('ru-RU')}
              </span>
            </div>
          </div>
        </div>

        {/* Config */}
        {template && (
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Настройки</h2>

            <div className="space-y-4">
              {template.config_schema.fields.map((field) => (
                <div key={field.name}>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    {field.label}
                  </label>

                  {field.type === 'select' ? (
                    <select
                      value={String(config[field.name] || '')}
                      onChange={(e) =>
                        setConfig((prev) => ({ ...prev, [field.name]: e.target.value }))
                      }
                      className="input"
                    >
                      {field.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : field.type === 'textarea' ? (
                    <textarea
                      value={String(config[field.name] || '')}
                      onChange={(e) =>
                        setConfig((prev) => ({ ...prev, [field.name]: e.target.value }))
                      }
                      className="input min-h-[100px]"
                      placeholder={field.placeholder}
                    />
                  ) : (
                    <input
                      type="text"
                      value={String(config[field.name] || '')}
                      onChange={(e) =>
                        setConfig((prev) => ({ ...prev, [field.name]: e.target.value }))
                      }
                      className="input"
                      placeholder={field.placeholder}
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="btn btn-primary flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Сохранение...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>Сохранить</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Действия</h2>

          <div className="flex flex-wrap gap-3">
            {bot.status === 'DRAFT' && (
              <button
                onClick={handleDeploy}
                className="btn btn-primary flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                <span>Активировать</span>
              </button>
            )}

            {bot.status === 'ACTIVE' && (
              <button className="btn btn-secondary flex items-center gap-2">
                <Pause className="w-4 h-4" />
                <span>Приостановить</span>
              </button>
            )}

            <button
              onClick={handleDelete}
              className="btn btn-danger flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              <span>Удалить</span>
            </button>
          </div>
        </div>
      </div>
    </Layout>
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
