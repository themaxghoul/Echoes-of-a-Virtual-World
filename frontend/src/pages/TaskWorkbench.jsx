import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft, Hammer, Clock, Zap, CheckCircle, XCircle, RefreshCw,
  ListChecks, Send, ChevronRight, Target, Cpu
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DIFFICULTY_COLORS = {
  trivial: 'border-zinc-500/40 text-zinc-400',
  easy: 'border-green-500/40 text-green-400',
  medium: 'border-blue-500/40 text-blue-400',
  hard: 'border-orange-500/40 text-orange-400',
  expert: 'border-purple-500/40 text-purple-400',
  legendary: 'border-yellow-500/40 text-yellow-400',
};

const TaskWorkbench = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const [available, setAvailable] = useState([]);
  const [myTasks, setMyTasks] = useState([]);
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTask, setActiveTask] = useState(null);
  const [outputValues, setOutputValues] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [busy, setBusy] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [availRes, mineRes, walRes] = await Promise.all([
        axios.get(`${API}/data-api/factory/tasks?status=available&limit=50`),
        axios.get(`${API}/data-api/factory/tasks?worker_id=${userId}&status=all&limit=50`),
        axios.get(`${API}/cosmetics/wallet/${userId}`)
      ]);
      setAvailable(availRes.data.tasks || []);
      setMyTasks(mineRes.data.tasks || []);
      setBalance(walRes.data.balance_ve || 0);
    } catch (e) {
      toast.error('Failed to load tasks');
    }
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    if (!userId) { navigate('/auth'); return; }
    loadData();
  }, [userId, navigate, loadData]);

  const claimTask = async (task) => {
    setBusy(task.instance_id);
    try {
      await axios.post(`${API}/data-api/factory/task/${task.instance_id}/claim?worker_id=${userId}`);
      toast.success(`Claimed: ${task.title}`);
      await loadData();
      setActiveTask({ ...task, status: 'claimed', claimed_by: userId });
      setOutputValues({});
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Claim failed');
    }
    setBusy(null);
  };

  const openWorkspace = (task) => {
    setActiveTask(task);
    setOutputValues({});
  };

  const buildOutput = (task) => {
    const spec = task.output_spec || {};
    const fieldTypes = spec.field_types || {};
    const output = {};
    for (const [field, raw] of Object.entries(outputValues)) {
      const t = fieldTypes[field];
      if (t === 'int') output[field] = parseInt(raw, 10);
      else if (t === 'float' || t === 'number') output[field] = parseFloat(raw);
      else if (t === 'list' || t === 'array') output[field] = raw.split('\n').map(s => s.trim()).filter(Boolean);
      else if (t === 'bool') output[field] = raw === 'true';
      else output[field] = raw;
    }
    return output;
  };

  const submitTask = async () => {
    if (!activeTask) return;
    setSubmitting(true);
    try {
      const res = await axios.post(`${API}/data-api/factory/task/${activeTask.instance_id}/submit`, {
        worker_id: userId,
        output: buildOutput(activeTask)
      });
      const { status, reward_ve, validation, boost_applied } = res.data;
      if (status === 'completed') {
        toast.success(`Task validated! +${reward_ve} VE$${boost_applied ? ' (Forge Surge boost applied!)' : ''}`);
      } else {
        const failed = (validation?.checks || []).filter(c => c.status !== 'present');
        toast.error(`Validation failed: ${failed.map(c => `${c.field || c.rule}: ${c.status}`).join(', ') || 'check your outputs'}`);
      }
      setActiveTask(null);
      await loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Submit failed');
    }
    setSubmitting(false);
  };

  const requiredFields = (task) => {
    const spec = task?.output_spec || {};
    const fields = [...(spec.required_fields || [])];
    Object.keys(spec.field_types || {}).forEach(f => { if (!fields.includes(f)) fields.push(f); });
    return fields;
  };

  const fieldInput = (task, field) => {
    const spec = task.output_spec || {};
    const t = (spec.field_types || {})[field];
    const constraint = (spec.constraints || {})[field] || {};
    if (t === 'list' || t === 'array') {
      return (
        <Textarea
          value={outputValues[field] || ''}
          onChange={(e) => setOutputValues(prev => ({ ...prev, [field]: e.target.value }))}
          placeholder="One entry per line"
          rows={3}
          data-testid={`output-field-${field}`}
        />
      );
    }
    if (t === 'int' || t === 'float' || t === 'number') {
      return (
        <Input
          type="number"
          value={outputValues[field] || ''}
          onChange={(e) => setOutputValues(prev => ({ ...prev, [field]: e.target.value }))}
          placeholder={`${constraint.min !== undefined ? `min ${constraint.min}` : ''} ${constraint.max !== undefined ? `max ${constraint.max}` : ''}`.trim() || 'Enter a number'}
          data-testid={`output-field-${field}`}
        />
      );
    }
    if ((constraint.min_length || 0) > 60) {
      return (
        <Textarea
          value={outputValues[field] || ''}
          onChange={(e) => setOutputValues(prev => ({ ...prev, [field]: e.target.value }))}
          placeholder={`Min ${constraint.min_length} characters`}
          rows={4}
          data-testid={`output-field-${field}`}
        />
      );
    }
    return (
      <Input
        value={outputValues[field] || ''}
        onChange={(e) => setOutputValues(prev => ({ ...prev, [field]: e.target.value }))}
        placeholder={constraint.min_length ? `Min ${constraint.min_length} characters` : 'Enter value'}
        data-testid={`output-field-${field}`}
      />
    );
  };

  const TaskCard = ({ task, actions }) => (
    <Card className="p-4 bg-surface/50 border-border/30" data-testid={`task-card-${task.instance_id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-medium truncate">{task.title}</h3>
          <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{task.objective}</p>
        </div>
        <Badge variant="outline" className={`shrink-0 capitalize ${DIFFICULTY_COLORS[task.difficulty] || ''}`}>{task.difficulty}</Badge>
      </div>
      <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground flex-wrap">
        <span className="text-green-400 font-bold">{task.reward_ve} VE$</span>
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{task.time_limit_minutes}m</span>
        {task.compute_cost > 0 && <span className="flex items-center gap-1"><Cpu className="w-3 h-3" />{task.compute_cost} compute</span>}
        {task.status !== 'available' && (
          <Badge variant="outline" className={`capitalize ${task.status === 'completed' ? 'border-green-500/40 text-green-400' : task.status === 'failed' ? 'border-red-500/40 text-red-400' : 'border-blue-500/40 text-blue-400'}`}>
            {task.status}
          </Badge>
        )}
      </div>
      <div className="mt-3">{actions}</div>
    </Card>
  );

  if (loading) {
    return <div className="min-h-screen bg-obsidian flex items-center justify-center"><RefreshCw className="w-8 h-8 text-gold animate-spin" /></div>;
  }

  const claimed = myTasks.filter(t => t.status === 'claimed');
  const finished = myTasks.filter(t => ['completed', 'failed'].includes(t.status));

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="workbench-back-btn">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Hammer className="w-6 h-6" /> Task Workbench
              </h1>
              <p className="text-sm text-muted-foreground">Claim factory tasks, complete them, earn VE$</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-green-500/10 text-green-400 border-green-500/30 text-base px-3 py-1" data-testid="workbench-ve-balance">
              {balance.toFixed(2)} VE$
            </Badge>
            <Button variant="outline" size="icon" onClick={loadData} className="border-border/40" data-testid="refresh-tasks-btn">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto p-4">
        {/* Active workspace */}
        {activeTask && (
          <Card className="p-5 mb-6 bg-surface/70 border-gold/30" data-testid="task-workspace">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="font-cinzel text-lg text-gold flex items-center gap-2"><Target className="w-5 h-5" />{activeTask.title}</h2>
                <p className="text-sm text-muted-foreground mt-1">{activeTask.objective}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setActiveTask(null)} data-testid="close-workspace-btn">Close</Button>
            </div>

            {Object.keys(activeTask.inputs || {}).length > 0 && (
              <div className="mt-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">Inputs</p>
                <pre className="text-xs bg-obsidian/60 p-3 rounded-sm border border-border/30 overflow-x-auto">{JSON.stringify(activeTask.inputs, null, 2)}</pre>
              </div>
            )}

            {(activeTask.process || []).length > 0 && (
              <div className="mt-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1"><ListChecks className="w-3.5 h-3.5" /> Process</p>
                <ol className="space-y-1.5">
                  {activeTask.process.map((step, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <span className="text-gold font-bold text-xs mt-0.5">{i + 1}.</span> {step}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            <div className="mt-5">
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-3">Your Output</p>
              {requiredFields(activeTask).length === 0 ? (
                <p className="text-sm text-muted-foreground italic">This task has no structured output spec — submit to mark complete.</p>
              ) : (
                <div className="space-y-4">
                  {requiredFields(activeTask).map(field => (
                    <div key={field}>
                      <Label className="capitalize">{field.replace(/_/g, ' ')} <span className="text-red-400">*</span></Label>
                      <div className="mt-1">{fieldInput(activeTask, field)}</div>
                    </div>
                  ))}
                </div>
              )}
              <Button onClick={submitTask} disabled={submitting} className="mt-4 bg-gold text-black hover:bg-gold-light" data-testid="submit-task-btn">
                {submitting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                Submit for Validation ({activeTask.reward_ve} VE$)
              </Button>
            </div>
          </Card>
        )}

        <Tabs defaultValue="available">
          <TabsList className="bg-surface/50">
            <TabsTrigger value="available" data-testid="tab-available">Available ({available.length})</TabsTrigger>
            <TabsTrigger value="active" data-testid="tab-active">My Active ({claimed.length})</TabsTrigger>
            <TabsTrigger value="history" data-testid="tab-history">History ({finished.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="available">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {available.length === 0 && <p className="text-muted-foreground text-sm col-span-2 italic">No tasks available right now. The factory scheduler generates new tasks every 5 minutes.</p>}
              {available.map(task => (
                <TaskCard key={task.instance_id} task={task} actions={
                  <Button size="sm" onClick={() => claimTask(task)} disabled={busy === task.instance_id}
                    className="bg-slate-blue hover:bg-slate-blue-light w-full" data-testid={`claim-${task.instance_id}`}>
                    {busy === task.instance_id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <>Claim Task <ChevronRight className="w-4 h-4 ml-1" /></>}
                  </Button>
                } />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="active">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {claimed.length === 0 && <p className="text-muted-foreground text-sm col-span-2 italic">No active tasks. Claim one from the Available tab.</p>}
              {claimed.map(task => (
                <TaskCard key={task.instance_id} task={task} actions={
                  <Button size="sm" onClick={() => openWorkspace(task)} className="bg-gold text-black hover:bg-gold-light w-full" data-testid={`work-${task.instance_id}`}>
                    <Hammer className="w-4 h-4 mr-1" /> Open Workspace
                  </Button>
                } />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="history">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {finished.length === 0 && <p className="text-muted-foreground text-sm col-span-2 italic">No completed tasks yet.</p>}
              {finished.map(task => (
                <TaskCard key={task.instance_id} task={task} actions={
                  <div className="flex items-center gap-2 text-xs">
                    {task.status === 'completed'
                      ? <span className="flex items-center gap-1 text-green-400"><CheckCircle className="w-4 h-4" /> Validated — earned {task.reward_ve} VE$</span>
                      : <span className="flex items-center gap-1 text-red-400"><XCircle className="w-4 h-4" /> Validation failed</span>}
                  </div>
                } />
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default TaskWorkbench;
