import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Bot, Check, Loader2 } from 'lucide-react';
import { Layout } from '../components/Layout';
import { botsApi, type BotTemplate } from '../api/client';

type Step = 'select' | 'configure' | 'confirm';

export function CreateBotPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('select');
  const [templates, setTemplates] = useState<Record<string, BotTemplate>>({});
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await botsApi.getTemplates();
      setTemplates(data.templates || {});
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectTemplate = (type: string) => {
    setSelectedTemplate(type);
    // Initialize config with defaults
    const template = templates[type];
    const defaults: Record<string, string> = {};
    template.config_schema.fields.forEach((field) => {
      if (field.default !== undefined) {
        defaults[field.name] = field.default;
      }
    });
    setConfig(defaults);
    setStep('configure');
  };

  const handleConfigChange = (name: string, value: string) => {
    setConfig((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreate = async () => {
    if (!selectedTemplate) return;

    setIsCreating(true);
    setError('');

    try {
      await botsApi.create({
        bot_type: selectedTemplate,
        config,
      });
      navigate('/bots');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка создания бота');
    } finally {
      setIsCreating(false);
    }
  };

  const template = selectedTemplate ? templates[selectedTemplate] : null;

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">Создать бота</h1>
          <p className="text-slate-400 mt-1">Выберите шаблон и настройте бота</p>
        </div>

        {/* Steps */}
        <div className="flex items-center gap-4 pb-6 border-b border-slate-700">
          <StepIndicator step={1} current={step === 'select'} completed={step !== 'select'}>
            Выбор шаблона
          </StepIndicator>
          <div className="flex-1 h-px bg-slate-700" />
          <StepIndicator step={2} current={step === 'configure'} completed={step === 'confirm'}>
            Настройка
          </StepIndicator>
          <div className="flex-1 h-px bg-slate-700" />
          <StepIndicator step={3} current={step === 'confirm'} completed={false}>
            Подтверждение
          </StepIndicator>
        </div>

        {/* Step 1: Select Template */}
        {step === 'select' && (
          <div className="space-y-4">
            {isLoading ? (
              <div className="text-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500 mx-auto" />
                <p className="text-slate-400 mt-4">Загрузка шаблонов...</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(templates).map(([type, tmpl]) => (
                  <button
                    key={type}
                    onClick={() => handleSelectTemplate(type)}
                    className="card text-left hover:border-primary-500 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Bot className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{tmpl.name}</h3>
                        <p className="text-sm text-slate-400 mt-1">{tmpl.description}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Configure */}
        {step === 'configure' && template && (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold text-white mb-6">
                Настройка: {template.name}
              </h2>

              <div className="space-y-4">
                {template.config_schema.fields.map((field) => (
                  <div key={field.name}>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      {field.label}
                      {field.required && <span className="text-red-400 ml-1">*</span>}
                    </label>

                    {field.type === 'select' ? (
                      <select
                        value={config[field.name] || ''}
                        onChange={(e) => handleConfigChange(field.name, e.target.value)}
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
                        value={config[field.name] || ''}
                        onChange={(e) => handleConfigChange(field.name, e.target.value)}
                        className="input min-h-[100px]"
                        placeholder={field.placeholder}
                      />
                    ) : (
                      <input
                        type="text"
                        value={config[field.name] || ''}
                        onChange={(e) => handleConfigChange(field.name, e.target.value)}
                        className="input"
                        placeholder={field.placeholder}
                      />
                    )}

                    {field.description && (
                      <p className="text-xs text-slate-500 mt-1">{field.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button
                onClick={() => setStep('select')}
                className="btn btn-secondary flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Назад</span>
              </button>
              <button
                onClick={() => setStep('confirm')}
                className="btn btn-primary flex items-center gap-2"
              >
                <span>Далее</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 'confirm' && template && (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold text-white mb-6">
                Подтверждение создания
              </h2>

              {error && (
                <div className="p-4 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm mb-6">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-slate-700">
                  <span className="text-slate-400">Тип бота</span>
                  <span className="text-white font-medium">{template.name}</span>
                </div>

                {template.config_schema.fields.map((field) => (
                  <div
                    key={field.name}
                    className="flex items-center justify-between py-3 border-b border-slate-700"
                  >
                    <span className="text-slate-400">{field.label}</span>
                    <span className="text-white">
                      {field.type === 'select'
                        ? field.options?.find((o) => o.value === config[field.name])?.label ||
                          config[field.name]
                        : config[field.name] || '-'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button
                onClick={() => setStep('configure')}
                className="btn btn-secondary flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Назад</span>
              </button>
              <button
                onClick={handleCreate}
                disabled={isCreating}
                className="btn btn-primary flex items-center gap-2"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Создание...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Создать бота</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

function StepIndicator({
  step,
  current,
  completed,
  children,
}: {
  step: number;
  current: boolean;
  completed: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          completed
            ? 'bg-green-600 text-white'
            : current
            ? 'bg-primary-600 text-white'
            : 'bg-slate-700 text-slate-400'
        }`}
      >
        {completed ? <Check className="w-4 h-4" /> : step}
      </div>
      <span
        className={`text-sm ${
          current || completed ? 'text-white' : 'text-slate-400'
        }`}
      >
        {children}
      </span>
    </div>
  );
}
