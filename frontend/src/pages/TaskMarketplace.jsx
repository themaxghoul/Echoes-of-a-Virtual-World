import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Plus, DollarSign, Coins, Clock, Star, CheckCircle, XCircle, Search, Filter, Briefcase, Send, Eye } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const TaskMarketplace = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tasks, setTasks] = useState([]);
  const [myTasks, setMyTasks] = useState({ created: [], accepted: [], completed: [] });
  const [categories, setCategories] = useState({});
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('browse');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTaskModal, setShowTaskModal] = useState(null);
  const [filter, setFilter] = useState({ category: '', paymentType: '' });
  
  const userId = localStorage.getItem('userId') || 'guest';

  useEffect(() => {
    fetchData();
    
    // Check for funding callback
    const funded = searchParams.get('funded');
    const taskId = searchParams.get('task_id');
    const sessionId = searchParams.get('session_id');
    
    if (funded === 'true' && sessionId) {
      checkFundingStatus(sessionId, taskId);
    }
  }, [searchParams]);

  const fetchData = async () => {
    try {
      const [tasksRes, categoriesRes, statsRes, myTasksRes] = await Promise.all([
        fetch(`${API}/api/task-marketplace/hybrid/tasks?status=open`),
        fetch(`${API}/api/task-marketplace/categories`),
        fetch(`${API}/api/task-marketplace/hybrid/stats`),
        fetch(`${API}/api/task-marketplace/hybrid/my-tasks/${userId}`)
      ]);
      
      if (tasksRes.ok) setTasks((await tasksRes.json()).tasks || []);
      if (categoriesRes.ok) setCategories((await categoriesRes.json()).categories || {});
      if (statsRes.ok) setStats(await statsRes.json());
      if (myTasksRes.ok) setMyTasks(await myTasksRes.json());
    } catch (err) {
      console.error('Failed to fetch marketplace data:', err);
    } finally {
      setLoading(false);
    }
  };

  const checkFundingStatus = async (sessionId, taskId) => {
    try {
      const res = await fetch(`${API}/api/task-marketplace/hybrid/funding-status/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.payment_status === 'paid') {
          toast.success('Task funded successfully! It is now live.');
          fetchData();
        }
      }
    } catch (err) {
      console.error('Failed to check funding status:', err);
    }
  };

  const filteredTasks = tasks.filter(task => {
    if (filter.category && task.category !== filter.category) return false;
    if (filter.paymentType && task.payment_type !== filter.paymentType) return false;
    return true;
  });

  const getPaymentBadge = (task) => {
    const type = task.payment_type;
    if (type === 've') return { icon: Coins, text: `${task.worker_payout_ve?.toFixed(2)} VE$`, color: 'bg-amber-500/20 text-amber-400' };
    if (type === 'stripe') return { icon: DollarSign, text: `$${task.worker_payout_stripe?.toFixed(2)}`, color: 'bg-green-500/20 text-green-400' };
    return { icon: Star, text: `${task.worker_payout_ve?.toFixed(2)} VE$ + $${task.worker_payout_stripe?.toFixed(2)}`, color: 'bg-purple-500/20 text-purple-400' };
  };

  const acceptTask = async (taskId) => {
    try {
      const res = await fetch(`${API}/api/task-marketplace/hybrid/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, worker_id: userId })
      });
      
      if (res.ok) {
        toast.success('Task accepted! Check My Tasks to submit your work.');
        fetchData();
        setShowTaskModal(null);
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to accept task');
      }
    } catch (err) {
      toast.error('Failed to accept task');
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-[#0f0f15]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/select-mode')} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold">Task Marketplace</h1>
              <p className="text-sm text-zinc-400">Earn VE$ and real money by completing tasks</p>
            </div>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-medium hover:opacity-90 transition-opacity"
            data-testid="create-task-btn"
          >
            <Plus className="w-4 h-4" />
            Post Task
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
            <div className="text-2xl font-bold text-amber-400">{stats.open_tasks || 0}</div>
            <div className="text-sm text-zinc-400">Open Tasks</div>
          </div>
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
            <div className="text-2xl font-bold text-green-400">{stats.completed_tasks || 0}</div>
            <div className="text-sm text-zinc-400">Completed</div>
          </div>
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
            <div className="text-2xl font-bold text-purple-400">{stats.total_ve_paid?.toFixed(0) || 0} VE$</div>
            <div className="text-sm text-zinc-400">Total Paid (VE$)</div>
          </div>
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
            <div className="text-2xl font-bold text-emerald-400">${stats.total_stripe_paid?.toFixed(2) || '0.00'}</div>
            <div className="text-sm text-zinc-400">Total Paid (USD)</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-zinc-800 pb-4">
          {[
            { id: 'browse', label: 'Browse Tasks', icon: Search },
            { id: 'my-work', label: 'My Work', icon: Briefcase },
            { id: 'my-tasks', label: 'Tasks I Posted', icon: Send }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.id 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Browse Tasks Tab */}
        {activeTab === 'browse' && (
          <>
            {/* Filters */}
            <div className="flex flex-wrap gap-4 mb-6">
              <select
                value={filter.category}
                onChange={e => setFilter({ ...filter, category: e.target.value })}
                className="bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-sm"
              >
                <option value="">All Categories</option>
                {Object.entries(categories).map(([key, cat]) => (
                  <option key={key} value={key}>{cat.name}</option>
                ))}
              </select>
              <select
                value={filter.paymentType}
                onChange={e => setFilter({ ...filter, paymentType: e.target.value })}
                className="bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-sm"
              >
                <option value="">All Payment Types</option>
                <option value="ve">VE$ Only</option>
                <option value="stripe">Real Money</option>
                <option value="hybrid">Hybrid (VE$ + USD)</option>
              </select>
            </div>

            {/* Task Grid */}
            {loading ? (
              <div className="text-center py-12 text-zinc-400">Loading tasks...</div>
            ) : filteredTasks.length === 0 ? (
              <div className="text-center py-12">
                <Briefcase className="w-12 h-12 mx-auto mb-4 text-zinc-600" />
                <p className="text-zinc-400">No tasks available. Be the first to post one!</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTasks.map(task => {
                  const payment = getPaymentBadge(task);
                  const catInfo = task.category_info || categories[task.category] || {};
                  
                  return (
                    <div
                      key={task.task_id}
                      className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 hover:border-purple-500/50 transition-colors cursor-pointer"
                      onClick={() => setShowTaskModal(task)}
                      data-testid={`task-card-${task.task_id}`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <span 
                          className="px-2 py-1 rounded text-xs font-medium"
                          style={{ backgroundColor: `${catInfo.color}20`, color: catInfo.color }}
                        >
                          {catInfo.name || task.category}
                        </span>
                        <span className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${payment.color}`}>
                          <payment.icon className="w-3 h-3" />
                          {payment.text}
                        </span>
                      </div>
                      
                      <h3 className="font-semibold mb-2 line-clamp-1">{task.title}</h3>
                      <p className="text-sm text-zinc-400 mb-4 line-clamp-2">{task.description}</p>
                      
                      <div className="flex items-center justify-between text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {task.time_estimate_minutes} min
                        </span>
                        <span className="capitalize px-2 py-0.5 rounded bg-zinc-800">
                          {task.difficulty}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* My Work Tab */}
        {activeTab === 'my-work' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-amber-400" />
                Active Tasks ({myTasks.accepted?.length || 0})
              </h3>
              {myTasks.accepted?.length === 0 ? (
                <p className="text-zinc-400 text-sm">No active tasks. Browse and accept tasks to get started.</p>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {myTasks.accepted?.map(task => (
                    <TaskCard key={task.task_id} task={task} categories={categories} onClick={() => setShowTaskModal(task)} />
                  ))}
                </div>
              )}
            </div>
            
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-400" />
                Completed ({myTasks.completed?.length || 0})
              </h3>
              {myTasks.completed?.length === 0 ? (
                <p className="text-zinc-400 text-sm">No completed tasks yet.</p>
              ) : (
                <div className="space-y-2">
                  {myTasks.completed?.map(sub => (
                    <div key={sub.submission_id} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 flex items-center justify-between">
                      <div>
                        <div className="font-medium">Task ID: {sub.task_id.slice(0, 8)}...</div>
                        <div className="text-sm text-zinc-400">Submitted: {new Date(sub.submitted_at).toLocaleDateString()}</div>
                      </div>
                      <div className="text-right">
                        {sub.ve_paid > 0 && <div className="text-amber-400 font-medium">{sub.ve_paid.toFixed(2)} VE$</div>}
                        {sub.stripe_paid > 0 && <div className="text-green-400 font-medium">${sub.stripe_paid.toFixed(2)}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* My Posted Tasks Tab */}
        {activeTab === 'my-tasks' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Tasks You Posted ({myTasks.created?.length || 0})</h3>
            {myTasks.created?.length === 0 ? (
              <div className="text-center py-12">
                <Send className="w-12 h-12 mx-auto mb-4 text-zinc-600" />
                <p className="text-zinc-400">You haven't posted any tasks yet.</p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 px-4 py-2 bg-purple-600 rounded-lg font-medium"
                >
                  Post Your First Task
                </button>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-4">
                {myTasks.created?.map(task => (
                  <TaskCard 
                    key={task.task_id} 
                    task={task} 
                    categories={categories} 
                    showStatus 
                    onClick={() => setShowTaskModal(task)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Create Task Modal */}
      {showCreateModal && (
        <CreateTaskModal 
          categories={categories}
          onClose={() => setShowCreateModal(false)}
          onCreated={(task) => {
            setShowCreateModal(false);
            fetchData();
            if (task.requires_stripe_funding) {
              toast.info('Task created! Complete Stripe payment to make it live.');
            } else {
              toast.success('Task posted successfully!');
            }
          }}
          userId={userId}
        />
      )}

      {/* Task Detail Modal */}
      {showTaskModal && (
        <TaskDetailModal
          task={showTaskModal}
          categories={categories}
          userId={userId}
          onClose={() => setShowTaskModal(null)}
          onAccept={acceptTask}
          onRefresh={fetchData}
        />
      )}
    </div>
  );
};

// Task Card Component
const TaskCard = ({ task, categories, showStatus, onClick }) => {
  const catInfo = task.category_info || categories[task.category] || {};
  
  return (
    <div
      className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 hover:border-purple-500/50 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <span 
          className="px-2 py-1 rounded text-xs font-medium"
          style={{ backgroundColor: `${catInfo.color}20`, color: catInfo.color }}
        >
          {catInfo.name || task.category}
        </span>
        {showStatus && (
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            task.status === 'open' ? 'bg-green-500/20 text-green-400' :
            task.status === 'completed' ? 'bg-blue-500/20 text-blue-400' :
            task.status === 'pending_funding' ? 'bg-amber-500/20 text-amber-400' :
            'bg-zinc-500/20 text-zinc-400'
          }`}>
            {task.status.replace('_', ' ')}
          </span>
        )}
      </div>
      <h3 className="font-semibold mb-1">{task.title}</h3>
      <p className="text-sm text-zinc-400 line-clamp-2">{task.description}</p>
    </div>
  );
};

// Create Task Modal
const CreateTaskModal = ({ categories, onClose, onCreated, userId }) => {
  const [form, setForm] = useState({
    category: 'data_labeling',
    title: '',
    description: '',
    instructions: '',
    difficulty: 'medium',
    payment_type: 've',
    ve_reward: 1,
    stripe_reward: 1,
    time_estimate_minutes: 10,
    max_completions: 1
  });
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!form.title || !form.description || !form.instructions) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/task-marketplace/hybrid/create?creator_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      
      if (res.ok) {
        const data = await res.json();
        
        if (data.requires_stripe_funding) {
          // Create Stripe checkout session
          const fundRes = await fetch(`${API}/api/task-marketplace/hybrid/fund-stripe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              task_id: data.task_id,
              origin_url: window.location.origin
            })
          });
          
          if (fundRes.ok) {
            const fundData = await fundRes.json();
            window.location.href = fundData.checkout_url;
          } else {
            toast.error('Failed to setup payment');
          }
        } else {
          onCreated(data);
        }
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to create task');
      }
    } catch (err) {
      toast.error('Failed to create task');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-zinc-800">
          <h2 className="text-xl font-bold">Post a New Task</h2>
          <p className="text-sm text-zinc-400">Create a task for other players to complete</p>
        </div>
        
        <div className="p-6 space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Category</label>
              <select
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              >
                {Object.entries(categories).map(([key, cat]) => (
                  <option key={key} value={key}>{cat.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Difficulty</label>
              <select
                value={form.difficulty}
                onChange={e => setForm({ ...form, difficulty: e.target.value })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              >
                <option value="trivial">Trivial</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
                <option value="expert">Expert</option>
                <option value="legendary">Legendary</option>
              </select>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Title *</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
              placeholder="Brief task title"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              data-testid="task-title-input"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Description *</label>
            <textarea
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              placeholder="What is this task about?"
              rows={3}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              data-testid="task-description-input"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Instructions *</label>
            <textarea
              value={form.instructions}
              onChange={e => setForm({ ...form, instructions: e.target.value })}
              placeholder="Step-by-step instructions for completing the task"
              rows={4}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              data-testid="task-instructions-input"
            />
          </div>
          
          <div className="border-t border-zinc-800 pt-4">
            <label className="block text-sm font-medium mb-3">Payment Type</label>
            <div className="flex gap-3">
              {[
                { id: 've', label: 'VE$ Only', icon: Coins, color: 'amber' },
                { id: 'stripe', label: 'Real Money', icon: DollarSign, color: 'green' },
                { id: 'hybrid', label: 'Hybrid', icon: Star, color: 'purple' }
              ].map(type => (
                <button
                  key={type.id}
                  onClick={() => setForm({ ...form, payment_type: type.id })}
                  className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border-2 transition-colors ${
                    form.payment_type === type.id 
                      ? `border-${type.color}-500 bg-${type.color}-500/10` 
                      : 'border-zinc-700 bg-zinc-800/50'
                  }`}
                  data-testid={`payment-type-${type.id}`}
                >
                  <type.icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{type.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            {(form.payment_type === 've' || form.payment_type === 'hybrid') && (
              <div>
                <label className="block text-sm font-medium mb-2">VE$ Reward</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={form.ve_reward}
                  onChange={e => setForm({ ...form, ve_reward: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
                  data-testid="ve-reward-input"
                />
              </div>
            )}
            {(form.payment_type === 'stripe' || form.payment_type === 'hybrid') && (
              <div>
                <label className="block text-sm font-medium mb-2">USD Reward</label>
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={form.stripe_reward}
                  onChange={e => setForm({ ...form, stripe_reward: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
                  data-testid="stripe-reward-input"
                />
              </div>
            )}
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Time Estimate (minutes)</label>
              <input
                type="number"
                min="1"
                value={form.time_estimate_minutes}
                onChange={e => setForm({ ...form, time_estimate_minutes: parseInt(e.target.value) || 10 })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Completions</label>
              <input
                type="number"
                min="1"
                value={form.max_completions}
                onChange={e => setForm({ ...form, max_completions: parseInt(e.target.value) || 1 })}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2"
              />
            </div>
          </div>
          
          <div className="bg-zinc-800/50 rounded-lg p-4 text-sm">
            <div className="font-medium mb-2">Payment Summary</div>
            <div className="space-y-1 text-zinc-400">
              {form.ve_reward > 0 && form.payment_type !== 'stripe' && (
                <div className="flex justify-between">
                  <span>VE$ to escrow:</span>
                  <span className="text-amber-400">{form.ve_reward.toFixed(2)} VE$</span>
                </div>
              )}
              {form.stripe_reward > 0 && form.payment_type !== 've' && (
                <div className="flex justify-between">
                  <span>USD payment:</span>
                  <span className="text-green-400">${form.stripe_reward.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-zinc-500">
                <span>Platform fee (10%):</span>
                <span>Deducted from worker payout</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="p-6 border-t border-zinc-800 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-zinc-800 rounded-lg font-medium hover:bg-zinc-700"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-medium hover:opacity-90 disabled:opacity-50"
            data-testid="submit-task-btn"
          >
            {loading ? 'Creating...' : form.payment_type !== 've' ? 'Continue to Payment' : 'Post Task'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Task Detail Modal
const TaskDetailModal = ({ task, categories, userId, onClose, onAccept, onRefresh }) => {
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [submissionText, setSubmissionText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submissions, setSubmissions] = useState([]);
  
  const catInfo = task.category_info || categories[task.category] || {};
  const isCreator = task.created_by === userId;
  const hasAccepted = task.accepted_workers?.includes(userId);
  
  useEffect(() => {
    if (isCreator) {
      fetchSubmissions();
    }
  }, [task.task_id]);

  const fetchSubmissions = async () => {
    // This would need an endpoint to get submissions for a task
    // For now we'll show a placeholder
  };

  const handleSubmit = async () => {
    if (!submissionText.trim()) {
      toast.error('Please provide your submission');
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/api/task-marketplace/hybrid/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.task_id,
          worker_id: userId,
          submission_data: { text: submissionText }
        })
      });
      
      if (res.ok) {
        toast.success('Submission sent! Waiting for review.');
        onRefresh();
        onClose();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to submit');
      }
    } catch (err) {
      toast.error('Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-start justify-between">
            <div>
              <span 
                className="inline-block px-2 py-1 rounded text-xs font-medium mb-2"
                style={{ backgroundColor: `${catInfo.color}20`, color: catInfo.color }}
              >
                {catInfo.name || task.category}
              </span>
              <h2 className="text-xl font-bold">{task.title}</h2>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-lg">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <div className="p-6 space-y-6">
          <div>
            <h3 className="font-semibold mb-2">Description</h3>
            <p className="text-zinc-300">{task.description}</p>
          </div>
          
          <div>
            <h3 className="font-semibold mb-2">Instructions</h3>
            <p className="text-zinc-300 whitespace-pre-wrap">{task.instructions}</p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <div className="text-xs text-zinc-400 mb-1">Difficulty</div>
              <div className="font-medium capitalize">{task.difficulty}</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <div className="text-xs text-zinc-400 mb-1">Time Est.</div>
              <div className="font-medium">{task.time_estimate_minutes} min</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <div className="text-xs text-zinc-400 mb-1">Completions</div>
              <div className="font-medium">{task.current_completions}/{task.max_completions}</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <div className="text-xs text-zinc-400 mb-1">Status</div>
              <div className="font-medium capitalize">{task.status?.replace('_', ' ')}</div>
            </div>
          </div>
          
          <div className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 border border-purple-500/30 rounded-xl p-4">
            <h3 className="font-semibold mb-3">Rewards (after 10% platform fee)</h3>
            <div className="flex flex-wrap gap-4">
              {task.worker_payout_ve > 0 && (
                <div className="flex items-center gap-2">
                  <Coins className="w-5 h-5 text-amber-400" />
                  <span className="text-lg font-bold text-amber-400">{task.worker_payout_ve?.toFixed(2)} VE$</span>
                </div>
              )}
              {task.worker_payout_stripe > 0 && (
                <div className="flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-400" />
                  <span className="text-lg font-bold text-green-400">${task.worker_payout_stripe?.toFixed(2)}</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Submit Work Form */}
          {hasAccepted && !showSubmitForm && (
            <button
              onClick={() => setShowSubmitForm(true)}
              className="w-full py-3 bg-green-600 rounded-lg font-medium hover:bg-green-700"
              data-testid="show-submit-form-btn"
            >
              Submit Your Work
            </button>
          )}
          
          {showSubmitForm && (
            <div className="border border-zinc-700 rounded-lg p-4">
              <h3 className="font-semibold mb-3">Submit Your Work</h3>
              <textarea
                value={submissionText}
                onChange={e => setSubmissionText(e.target.value)}
                placeholder="Describe your completed work or paste your deliverable..."
                rows={5}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 mb-3"
                data-testid="submission-text-input"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => setShowSubmitForm(false)}
                  className="px-4 py-2 bg-zinc-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="flex-1 py-2 bg-green-600 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
                  data-testid="submit-work-btn"
                >
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Actions */}
        {!isCreator && !hasAccepted && task.status === 'open' && (
          <div className="p-6 border-t border-zinc-800">
            <button
              onClick={() => onAccept(task.task_id)}
              className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg font-medium hover:opacity-90"
              data-testid="accept-task-btn"
            >
              Accept This Task
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskMarketplace;
