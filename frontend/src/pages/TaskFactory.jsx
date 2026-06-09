import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, Plus, Play, Pause, RefreshCw, Clock, Zap, CheckCircle, 
  XCircle, AlertCircle, Settings, Trash2, Edit, ChevronRight, Factory
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const TaskFactory = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState(null);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('templates');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [templatesRes, tasksRes, statsRes, schedulerRes] = await Promise.all([
        fetch(`${API}/api/data-api/factory/templates`),
        fetch(`${API}/api/data-api/factory/tasks?limit=20`),
        fetch(`${API}/api/data-api/factory/stats`),
        fetch(`${API}/api/data-api/scheduler/status`)
      ]);
      
      if (templatesRes.ok) setTemplates((await templatesRes.json()).templates || []);
      if (tasksRes.ok) setTasks((await tasksRes.json()).tasks || []);
      if (statsRes.ok) setStats(await statsRes.json());
      if (schedulerRes.ok) setSchedulerStatus(await schedulerRes.json());
    } catch (err) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const runScheduler = async () => {
    try {
      const res = await fetch(`${API}/api/data-api/scheduler/run`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Scheduler ran: ${data.templates_processed} templates processed`);
        fetchData();
      }
    } catch (err) {
      toast.error('Scheduler failed');
    }
  };

  const toggleAutoRepeat = async (templateId, enabled) => {
    try {
      const res = await fetch(`${API}/api/data-api/scheduler/template/${templateId}/toggle?enabled=${enabled}`, { method: 'POST' });
      if (res.ok) {
        toast.success(enabled ? 'Auto-repeat enabled' : 'Auto-repeat disabled');
        fetchData();
      }
    } catch (err) {
      toast.error('Failed to toggle');
    }
  };

  const generateTasks = async (templateId, count = 5) => {
    try {
      const res = await fetch(`${API}/api/data-api/factory/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id: templateId, count })
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Generated ${data.generated} tasks`);
        fetchData();
      }
    } catch (err) {
      toast.error('Failed to generate');
    }
  };

  const claimTask = async (instanceId) => {
    try {
      const res = await fetch(`${API}/api/data-api/factory/task/${instanceId}/claim?worker_id=${userId}`, { method: 'POST' });
      if (res.ok) {
        toast.success('Task claimed!');
        fetchData();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Claim failed');
      }
    } catch (err) {
      toast.error('Failed to claim');
    }
  };

  const deleteTemplate = async (templateId) => {
    if (!window.confirm('Deactivate this template?')) return;
    try {
      const res = await fetch(`${API}/api/data-api/factory/template/${templateId}?admin_id=${userId}`, { method: 'DELETE' });
      if (res.ok) {
        toast.success('Template deactivated');
        fetchData();
      }
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  const difficultyColors = {
    trivial: 'text-zinc-400 bg-zinc-400/10',
    easy: 'text-green-400 bg-green-400/10',
    medium: 'text-blue-400 bg-blue-400/10',
    hard: 'text-yellow-400 bg-yellow-400/10',
    expert: 'text-orange-400 bg-orange-400/10',
    legendary: 'text-red-400 bg-red-400/10'
  };

  const statusColors = {
    available: 'text-green-400',
    claimed: 'text-yellow-400',
    completed: 'text-blue-400',
    failed: 'text-red-400'
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-black flex items-center justify-center">
        <Factory className="w-12 h-12 text-amber-400 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-black text-white">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-amber-900/30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-amber-400 hover:text-amber-300" data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold text-amber-400 flex items-center gap-2">
            <Factory className="w-5 h-5" /> Task Factory
          </h1>
          <div className="flex items-center gap-2">
            <button onClick={runScheduler} className="p-2 text-green-400 hover:bg-green-400/10 rounded-lg" title="Run Scheduler" data-testid="run-scheduler-btn">
              <Play className="w-5 h-5" />
            </button>
            <button onClick={fetchData} className="p-2 text-zinc-400 hover:text-amber-400" data-testid="refresh-btn">
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="pt-20 pb-8 px-4 max-w-7xl mx-auto">
        {/* Stats Bar */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
              <div className="text-2xl font-bold text-amber-400">{stats.templates?.active || 0}</div>
              <div className="text-sm text-zinc-400">Active Templates</div>
            </div>
            <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
              <div className="text-2xl font-bold text-green-400">{stats.instances?.by_status?.available || 0}</div>
              <div className="text-sm text-zinc-400">Available Tasks</div>
            </div>
            <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
              <div className="text-2xl font-bold text-blue-400">{stats.instances?.by_status?.completed || 0}</div>
              <div className="text-sm text-zinc-400">Completed</div>
            </div>
            <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
              <div className="text-2xl font-bold text-amber-400">{stats.economics?.total_ve_paid?.toFixed(2) || 0}</div>
              <div className="text-sm text-zinc-400">VE$ Paid</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {['templates', 'tasks', 'scheduler'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium capitalize transition-all ${
                activeTab === tab ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-zinc-800/50 text-zinc-400 hover:text-zinc-300'
              }`}
              data-testid={`tab-${tab}`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-zinc-300">Task Templates</h2>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-black font-medium rounded-lg"
                data-testid="create-template-btn"
              >
                <Plus className="w-4 h-4" /> New Template
              </button>
            </div>

            {templates.length === 0 ? (
              <div className="p-8 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                <Factory className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                <p className="text-zinc-400">No templates yet</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {templates.map((t, idx) => (
                  <div key={t.template_id} className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50" data-testid={`template-${idx}`}>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-medium text-white">{t.title}</h3>
                        <p className="text-sm text-zinc-400 mt-1">{t.objective}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${difficultyColors[t.difficulty] || difficultyColors.medium}`}>
                          {t.difficulty}
                        </span>
                        {t.auto_repeat && (
                          <span className="px-2 py-0.5 rounded text-xs bg-green-500/20 text-green-400">AUTO</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-zinc-500 mb-3">
                      <span>VE${t.adjusted_reward_ve?.toFixed(2) || t.reward_ve}</span>
                      <span>{t.time_limit_minutes}min</span>
                      <span>{t.stats?.instances_created || 0} created</span>
                      <span>{t.stats?.instances_completed || 0} completed</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => generateTasks(t.template_id, 5)}
                        className="px-3 py-1.5 bg-amber-600/20 text-amber-400 rounded-lg text-sm hover:bg-amber-600/30"
                        data-testid={`generate-${idx}`}
                      >
                        Generate 5
                      </button>
                      <button
                        onClick={() => toggleAutoRepeat(t.template_id, !t.auto_repeat)}
                        className={`px-3 py-1.5 rounded-lg text-sm ${t.auto_repeat ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}
                        data-testid={`toggle-${idx}`}
                      >
                        {t.auto_repeat ? <Pause className="w-4 h-4 inline mr-1" /> : <Play className="w-4 h-4 inline mr-1" />}
                        {t.auto_repeat ? 'Stop' : 'Start'} Auto
                      </button>
                      <button
                        onClick={() => setSelectedTemplate(t)}
                        className="px-3 py-1.5 bg-zinc-700/50 text-zinc-300 rounded-lg text-sm hover:bg-zinc-700"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteTemplate(t.template_id)}
                        className="px-3 py-1.5 bg-red-500/10 text-red-400 rounded-lg text-sm hover:bg-red-500/20"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tasks Tab */}
        {activeTab === 'tasks' && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-zinc-300">Available Tasks</h2>
            
            {tasks.length === 0 ? (
              <div className="p-8 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                <p className="text-zinc-400">No available tasks</p>
              </div>
            ) : (
              <div className="space-y-3">
                {tasks.map((task, idx) => (
                  <div key={task.instance_id} className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50" data-testid={`task-${idx}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-white">{task.title}</h3>
                          <span className={`text-xs ${statusColors[task.status]}`}>{task.status}</span>
                        </div>
                        <p className="text-sm text-zinc-400">{task.objective}</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-zinc-500">
                          <span className={`px-2 py-0.5 rounded ${difficultyColors[task.difficulty]}`}>{task.difficulty}</span>
                          <span>VE${task.reward_ve?.toFixed(2)}</span>
                          <span><Clock className="w-3 h-3 inline mr-1" />{task.time_limit_minutes}min</span>
                        </div>
                      </div>
                      {task.status === 'available' && (
                        <button
                          onClick={() => claimTask(task.instance_id)}
                          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-black font-medium rounded-lg text-sm"
                          data-testid={`claim-${idx}`}
                        >
                          Claim
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Scheduler Tab */}
        {activeTab === 'scheduler' && schedulerStatus && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-zinc-300">Auto-Repeat Scheduler</h2>
              <button
                onClick={runScheduler}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-black font-medium rounded-lg"
                data-testid="run-scheduler-btn-2"
              >
                <Play className="w-4 h-4" /> Run Now
              </button>
            </div>

            <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50">
              <div className="text-sm text-zinc-400 mb-2">Current Time</div>
              <div className="font-mono text-white">{new Date(schedulerStatus.current_time).toLocaleString()}</div>
            </div>

            {schedulerStatus.auto_repeat_templates?.length === 0 ? (
              <div className="p-8 rounded-xl bg-zinc-800/50 border border-zinc-700/50 text-center">
                <Clock className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                <p className="text-zinc-400">No auto-repeat templates configured</p>
              </div>
            ) : (
              <div className="space-y-3">
                {schedulerStatus.auto_repeat_templates.map((t, idx) => (
                  <div key={t.template_id} className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700/50" data-testid={`scheduler-${idx}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium text-white">{t.title}</h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-zinc-500">
                          <span>Every {t.repeat_interval_minutes}min</span>
                          <span>Batch: {t.repeat_batch_size}</span>
                          <span>Available: {t.current_available}/{t.max_instances}</span>
                        </div>
                      </div>
                      <div className="text-right">
                        {t.is_due ? (
                          <span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400">DUE NOW</span>
                        ) : (
                          <span className="text-xs text-zinc-500">
                            Next: {t.next_repeat_at ? new Date(t.next_repeat_at).toLocaleTimeString() : 'N/A'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Create Template Modal */}
      {showCreateModal && (
        <CreateTemplateModal onClose={() => setShowCreateModal(false)} onCreated={() => { setShowCreateModal(false); fetchData(); }} />
      )}

      {/* Template Settings Modal */}
      {selectedTemplate && (
        <TemplateSettingsModal template={selectedTemplate} onClose={() => setSelectedTemplate(null)} onUpdated={() => { setSelectedTemplate(null); fetchData(); }} />
      )}
    </div>
  );
};

const CreateTemplateModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({
    title: '',
    objective: '',
    task_type: 'general',
    difficulty: 'medium',
    reward_ve: 0.05,
    time_limit_minutes: 30,
    auto_repeat: false,
    repeat_interval_minutes: 60,
    repeat_batch_size: 10,
    max_instances: 100
  });
  const [creating, setCreating] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await fetch(`${API}/api/data-api/factory/template?creator_id=${localStorage.getItem('userId') || 'system'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          inputs: {},
          process: [],
          output: { required_fields: [], field_types: {}, constraints: {} },
          validation: { type: 'auto', rules: [] },
          dependencies: []
        })
      });
      if (res.ok) {
        toast.success('Template created!');
        onCreated();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to create');
      }
    } catch (err) {
      toast.error('Failed to create template');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 rounded-xl border border-zinc-700 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-zinc-700 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Create Template</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Title</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm({...form, title: e.target.value})}
              className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
              required
              data-testid="input-title"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Objective</label>
            <textarea
              value={form.objective}
              onChange={e => setForm({...form, objective: e.target.value})}
              className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
              rows={2}
              required
              data-testid="input-objective"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Type</label>
              <select
                value={form.task_type}
                onChange={e => setForm({...form, task_type: e.target.value})}
                className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
                data-testid="input-type"
              >
                <option value="general">General</option>
                <option value="labeling">Labeling</option>
                <option value="classification">Classification</option>
                <option value="generation">Generation</option>
                <option value="validation">Validation</option>
                <option value="research">Research</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Difficulty</label>
              <select
                value={form.difficulty}
                onChange={e => setForm({...form, difficulty: e.target.value})}
                className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
                data-testid="input-difficulty"
              >
                <option value="trivial">Trivial (0.5x)</option>
                <option value="easy">Easy (0.75x)</option>
                <option value="medium">Medium (1x)</option>
                <option value="hard">Hard (1.5x)</option>
                <option value="expert">Expert (2x)</option>
                <option value="legendary">Legendary (3x)</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Reward VE$</label>
              <input
                type="number"
                step="0.01"
                value={form.reward_ve}
                onChange={e => setForm({...form, reward_ve: parseFloat(e.target.value)})}
                className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
                data-testid="input-reward"
              />
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1">Time Limit (min)</label>
              <input
                type="number"
                value={form.time_limit_minutes}
                onChange={e => setForm({...form, time_limit_minutes: parseInt(e.target.value)})}
                className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
                data-testid="input-time"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto_repeat"
              checked={form.auto_repeat}
              onChange={e => setForm({...form, auto_repeat: e.target.checked})}
              className="w-4 h-4"
              data-testid="input-auto-repeat"
            />
            <label htmlFor="auto_repeat" className="text-sm text-zinc-400">Enable Auto-Repeat</label>
          </div>
          {form.auto_repeat && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Interval (min)</label>
                <input
                  type="number"
                  value={form.repeat_interval_minutes}
                  onChange={e => setForm({...form, repeat_interval_minutes: parseInt(e.target.value)})}
                  className="w-full px-2 py-1 bg-black/50 border border-zinc-700 rounded text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Batch Size</label>
                <input
                  type="number"
                  value={form.repeat_batch_size}
                  onChange={e => setForm({...form, repeat_batch_size: parseInt(e.target.value)})}
                  className="w-full px-2 py-1 bg-black/50 border border-zinc-700 rounded text-white text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Max Instances</label>
                <input
                  type="number"
                  value={form.max_instances}
                  onChange={e => setForm({...form, max_instances: parseInt(e.target.value)})}
                  className="w-full px-2 py-1 bg-black/50 border border-zinc-700 rounded text-white text-sm"
                />
              </div>
            </div>
          )}
          <button
            type="submit"
            disabled={creating}
            className="w-full py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-black font-medium rounded-lg"
            data-testid="submit-template"
          >
            {creating ? 'Creating...' : 'Create Template'}
          </button>
        </form>
      </div>
    </div>
  );
};

const TemplateSettingsModal = ({ template, onClose, onUpdated }) => {
  const [interval, setInterval] = useState(template.repeat_interval_minutes || 60);
  const [batchSize, setBatchSize] = useState(template.repeat_batch_size || 10);
  const [maxInstances, setMaxInstances] = useState(template.max_instances || 100);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(
        `${API}/api/data-api/scheduler/template/${template.template_id}/config?interval_minutes=${interval}&batch_size=${batchSize}&max_instances=${maxInstances}`,
        { method: 'PUT' }
      );
      if (res.ok) {
        toast.success('Settings updated');
        onUpdated();
      }
    } catch (err) {
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 rounded-xl border border-zinc-700 w-full max-w-md">
        <div className="p-4 border-b border-zinc-700 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Template Settings</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">&times;</button>
        </div>
        <div className="p-4 space-y-4">
          <div className="text-white font-medium">{template.title}</div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Repeat Interval (minutes)</label>
            <input
              type="number"
              value={interval}
              onChange={e => setInterval(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Batch Size</label>
            <input
              type="number"
              value={batchSize}
              onChange={e => setBatchSize(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1">Max Instances</label>
            <input
              type="number"
              value={maxInstances}
              onChange={e => setMaxInstances(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-black/50 border border-zinc-700 rounded-lg text-white"
            />
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-black font-medium rounded-lg"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TaskFactory;
