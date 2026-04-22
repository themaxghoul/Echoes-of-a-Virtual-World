import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, Play, Pause, CheckCircle, Clock, DollarSign,
  RefreshCw, Zap, TrendingUp, Image, FileText, Mic,
  MessageSquare, Tag, Shield, Brain, Sparkles, Trophy,
  Star, Target, BarChart3, Users, Award
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatVE = (amount) => {
  if (amount === null || amount === undefined) return 'VE$0.00';
  return `VE$${parseFloat(amount).toFixed(2)}`;
};

// Task type icons and colors
const TASK_CONFIG = {
  image_tagging: { icon: Image, color: 'bg-blue-500', name: 'Image Tagging' },
  image_comparison: { icon: Image, color: 'bg-indigo-500', name: 'Image Comparison' },
  content_rating: { icon: Shield, color: 'bg-red-500', name: 'Content Rating' },
  sentiment_label: { icon: MessageSquare, color: 'bg-green-500', name: 'Sentiment Labeling' },
  text_categorization: { icon: Tag, color: 'bg-purple-500', name: 'Text Categorization' },
  spam_detection: { icon: Shield, color: 'bg-orange-500', name: 'Spam Detection' },
  audio_transcription_short: { icon: Mic, color: 'bg-cyan-500', name: 'Audio Transcription' },
  response_ranking: { icon: Brain, color: 'bg-pink-500', name: 'AI Response Ranking' },
  prompt_writing: { icon: Sparkles, color: 'bg-yellow-500', name: 'Prompt Writing' },
  captcha_solving: { icon: CheckCircle, color: 'bg-gray-500', name: 'CAPTCHA Solving' },
  data_entry: { icon: FileText, color: 'bg-teal-500', name: 'Data Entry' },
  npc_dialogue_rating: { icon: Users, color: 'bg-violet-500', name: 'NPC Dialogue Rating' },
  world_description: { icon: Sparkles, color: 'bg-amber-500', name: 'World Description' },
};

const TasksDashboard = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  
  const [loading, setLoading] = useState(true);
  const [taskTypes, setTaskTypes] = useState({});
  const [activeSession, setActiveSession] = useState(null);
  const [currentTasks, setCurrentTasks] = useState([]);
  const [taskTimer, setTaskTimer] = useState(0);
  const [workerStats, setWorkerStats] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [platformStats, setPlatformStats] = useState(null);
  const [completedCount, setCompletedCount] = useState(0);
  const [sessionEarnings, setSessionEarnings] = useState(0);

  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [typesRes, statsRes, leaderRes, platformRes] = await Promise.all([
        axios.get(`${API}/rt-tasks/types`),
        axios.get(`${API}/rt-tasks/worker/${userId}/stats`).catch(() => ({ data: null })),
        axios.get(`${API}/rt-tasks/leaderboard/hourly?limit=10`).catch(() => ({ data: { leaderboard: [] } })),
        axios.get(`${API}/rt-tasks/platform/stats`).catch(() => ({ data: null }))
      ]);
      
      setTaskTypes(typesRes.data.task_types || {});
      setWorkerStats(statsRes.data);
      setLeaderboard(leaderRes.data.leaderboard || []);
      setPlatformStats(platformRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load task data');
    }
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadData();
  }, [userId, navigate, loadData]);

  // Task timer
  useEffect(() => {
    let interval;
    if (activeSession) {
      interval = setInterval(() => {
        setTaskTimer(t => t + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [activeSession]);

  // Start task session
  const startSession = async (taskType) => {
    try {
      const res = await axios.post(`${API}/rt-tasks/session/start`, {
        worker_id: userId,
        worker_type: 'player',
        task_type: taskType
      });
      
      setActiveSession({
        sessionId: res.data.session_id,
        taskType: taskType,
        payoutPerTask: res.data.payout_per_task,
        estimatedHourly: res.data.estimated_hourly
      });
      setCurrentTasks(res.data.tasks || []);
      setTaskTimer(0);
      setCompletedCount(0);
      setSessionEarnings(0);
      toast.success(`Started ${TASK_CONFIG[taskType]?.name || taskType} session`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start session');
    }
  };

  // Complete task
  const completeTask = async (task, response) => {
    try {
      const res = await axios.post(`${API}/rt-tasks/task/complete`, {
        task_id: task.task_id,
        worker_id: userId,
        response: response,
        time_taken_seconds: taskTimer
      });
      
      if (res.data.completed) {
        setCompletedCount(c => c + 1);
        setSessionEarnings(e => e + res.data.payout);
        toast.success(`+${formatVE(res.data.payout)}`);
        
        // Remove completed task and load more if needed
        setCurrentTasks(prev => prev.filter(t => t.task_id !== task.task_id));
        
        if (currentTasks.length <= 3 && activeSession) {
          loadMoreTasks();
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete task');
    }
  };

  // Load more tasks
  const loadMoreTasks = async () => {
    if (!activeSession) return;
    
    try {
      const res = await axios.get(`${API}/rt-tasks/session/${activeSession.sessionId}/next-batch?count=5`);
      setCurrentTasks(prev => [...prev, ...(res.data.tasks || [])]);
    } catch (error) {
      console.error('Failed to load more tasks:', error);
    }
  };

  // End session
  const endSession = async () => {
    if (!activeSession) return;
    
    try {
      await axios.post(`${API}/rt-tasks/session/${activeSession.sessionId}/end`);
      toast.success(`Session ended! Completed ${completedCount} tasks, earned ${formatVE(sessionEarnings)}`);
      setActiveSession(null);
      setCurrentTasks([]);
      setTaskTimer(0);
      loadData();
    } catch (error) {
      toast.error('Failed to end session');
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Render task UI based on type
  const renderTaskUI = (task) => {
    const taskData = task.data || {};
    
    switch (task.task_type) {
      case 'sentiment_label':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-black/30 rounded-lg">
              <p className="text-lg italic">"{taskData.text}"</p>
            </div>
            <div className="flex gap-3">
              {(taskData.options || ['positive', 'negative', 'neutral']).map(opt => (
                <Button
                  key={opt}
                  onClick={() => completeTask(task, { sentiment: opt })}
                  className={`flex-1 ${
                    opt === 'positive' ? 'bg-green-600 hover:bg-green-500' :
                    opt === 'negative' ? 'bg-red-600 hover:bg-red-500' :
                    'bg-gray-600 hover:bg-gray-500'
                  }`}
                  data-testid={`sentiment-${opt}-btn`}
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        );
        
      case 'content_rating':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-black/30 rounded-lg">
              <p>{taskData.content_preview || 'Content to review'}</p>
            </div>
            <div className="flex gap-3">
              {(taskData.options || ['safe', 'questionable', 'unsafe']).map(opt => (
                <Button
                  key={opt}
                  onClick={() => completeTask(task, { rating: opt })}
                  className={`flex-1 ${
                    opt === 'safe' ? 'bg-green-600 hover:bg-green-500' :
                    opt === 'questionable' ? 'bg-yellow-600 hover:bg-yellow-500' :
                    'bg-red-600 hover:bg-red-500'
                  }`}
                  data-testid={`rating-${opt}-btn`}
                >
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </Button>
              ))}
            </div>
          </div>
        );
        
      case 'npc_dialogue_rating':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-black/30 rounded-lg">
              <div className="text-gold font-medium mb-2">{taskData.npc_name}</div>
              <p className="text-lg italic">"{taskData.dialogue}"</p>
              <p className="text-xs text-muted-foreground mt-2">Context: {taskData.context}</p>
            </div>
            <div className="flex gap-3">
              {[1, 2, 3, 4, 5].map(rating => (
                <Button
                  key={rating}
                  onClick={() => completeTask(task, { rating })}
                  className="flex-1 bg-purple-600 hover:bg-purple-500"
                  data-testid={`npc-rating-${rating}-btn`}
                >
                  {rating} <Star className="w-4 h-4 ml-1" />
                </Button>
              ))}
            </div>
          </div>
        );
        
      case 'response_ranking':
        return (
          <div className="space-y-4">
            <div className="p-3 bg-black/30 rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Prompt:</p>
              <p className="font-medium">{taskData.prompt}</p>
            </div>
            <div className="space-y-2">
              {(taskData.responses || []).map((resp, idx) => (
                <Button
                  key={idx}
                  onClick={() => completeTask(task, { best_response: idx })}
                  variant="outline"
                  className="w-full text-left justify-start h-auto p-3 hover:bg-gold/10 hover:border-gold/50"
                  data-testid={`response-${idx}-btn`}
                >
                  <span className="text-gold mr-2">{idx + 1}.</span>
                  {resp}
                </Button>
              ))}
            </div>
          </div>
        );
        
      default:
        return (
          <div className="space-y-4">
            <div className="p-4 bg-black/30 rounded-lg">
              <p>{taskData.instructions || task.task_type}</p>
            </div>
            <Button
              onClick={() => completeTask(task, { completed: true })}
              className="w-full bg-gold text-black hover:bg-gold-light"
              data-testid="complete-task-btn"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Mark Complete
            </Button>
          </div>
        );
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Tasks Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      {/* Header */}
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/earnings')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Zap className="w-6 h-6" />
                Real-Time Tasks
              </h1>
              <p className="text-sm text-muted-foreground">Quick tasks, instant payouts</p>
            </div>
          </div>
          
          {/* Session info */}
          {activeSession && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-lg font-bold text-gold">{formatVE(sessionEarnings)}</div>
                <div className="text-xs text-muted-foreground">{completedCount} tasks</div>
              </div>
              <Badge className="bg-green-500/20 text-green-400">
                <Clock className="w-3 h-3 mr-1" />
                {formatTime(taskTimer)}
              </Badge>
              <Button variant="destructive" size="sm" onClick={endSession}>
                <Pause className="w-4 h-4 mr-1" />
                End Session
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4">
        {activeSession ? (
          /* Active Session View */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Task Area */}
            <div className="lg:col-span-2">
              <Card className="bg-surface/50 border-border/30 p-6">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    {(() => {
                      const config = TASK_CONFIG[activeSession.taskType] || {};
                      const Icon = config.icon || Zap;
                      return (
                        <>
                          <div className={`w-12 h-12 rounded-lg ${config.color || 'bg-gold'} flex items-center justify-center`}>
                            <Icon className="w-6 h-6 text-white" />
                          </div>
                          <div>
                            <h2 className="font-cinzel text-xl">{config.name || activeSession.taskType}</h2>
                            <p className="text-sm text-muted-foreground">
                              {formatVE(activeSession.payoutPerTask)}/task • ~{formatVE(activeSession.estimatedHourly)}/hr
                            </p>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                  <Badge className="bg-gold/20 text-gold">
                    {currentTasks.length} tasks queued
                  </Badge>
                </div>

                {/* Current Task */}
                {currentTasks.length > 0 ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-gold/5 border border-gold/20 rounded-lg">
                      {renderTaskUI(currentTasks[0])}
                    </div>
                    
                    {/* Skip option */}
                    <div className="flex justify-center">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => setCurrentTasks(prev => [...prev.slice(1), prev[0]])}
                        className="text-muted-foreground hover:text-foreground"
                        data-testid="skip-task-btn"
                      >
                        Skip this task
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <RefreshCw className="w-8 h-8 text-muted-foreground mx-auto mb-3 animate-spin" />
                    <p>Loading more tasks...</p>
                  </div>
                )}
              </Card>
            </div>

            {/* Session Stats */}
            <div className="space-y-4">
              <Card className="p-6 bg-gradient-to-br from-gold/20 to-gold/5 border-gold/30">
                <h3 className="font-cinzel text-lg text-gold mb-4">Session Stats</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Earnings</span>
                      <span className="text-gold font-bold">{formatVE(sessionEarnings)}</span>
                    </div>
                    <Progress value={Math.min(100, (sessionEarnings / 10) * 100)} className="h-2" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-black/20 rounded-lg">
                      <div className="text-2xl font-bold text-foreground">{completedCount}</div>
                      <div className="text-xs text-muted-foreground">Completed</div>
                    </div>
                    <div className="text-center p-3 bg-black/20 rounded-lg">
                      <div className="text-2xl font-bold text-foreground">{formatTime(taskTimer)}</div>
                      <div className="text-xs text-muted-foreground">Time</div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Tips */}
              <Card className="p-4 bg-surface/50 border-border/30">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-yellow-500" />
                  Pro Tips
                </h4>
                <ul className="text-sm text-muted-foreground space-y-2">
                  <li>• Focus on accuracy over speed</li>
                  <li>• Take short breaks every 30 min</li>
                  <li>• Consistent work = bonus multipliers</li>
                </ul>
              </Card>
            </div>
          </div>
        ) : (
          /* Task Selection View */
          <Tabs defaultValue="tasks" className="space-y-6">
            <TabsList className="bg-surface/50">
              <TabsTrigger value="tasks">Available Tasks</TabsTrigger>
              <TabsTrigger value="stats">My Stats</TabsTrigger>
              <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
            </TabsList>

            <TabsContent value="tasks" className="space-y-6">
              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-surface/50 border-border/30">
                  <div className="flex items-center gap-3">
                    <DollarSign className="w-8 h-8 text-gold" />
                    <div>
                      <div className="text-2xl font-bold">{formatVE(workerStats?.total_earnings || 0)}</div>
                      <div className="text-xs text-muted-foreground">Total Earned</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-surface/50 border-border/30">
                  <div className="flex items-center gap-3">
                    <Target className="w-8 h-8 text-purple-500" />
                    <div>
                      <div className="text-2xl font-bold">{workerStats?.total_tasks || 0}</div>
                      <div className="text-xs text-muted-foreground">Tasks Done</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-surface/50 border-border/30">
                  <div className="flex items-center gap-3">
                    <Users className="w-8 h-8 text-cyan-500" />
                    <div>
                      <div className="text-2xl font-bold">{platformStats?.active_workers || 0}</div>
                      <div className="text-xs text-muted-foreground">Active Workers</div>
                    </div>
                  </div>
                </Card>
                <Card className="p-4 bg-surface/50 border-border/30">
                  <div className="flex items-center gap-3">
                    <BarChart3 className="w-8 h-8 text-green-500" />
                    <div>
                      <div className="text-2xl font-bold">{platformStats?.tasks_completed_hour || 0}</div>
                      <div className="text-xs text-muted-foreground">Tasks/Hour</div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Task Types Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(taskTypes).map(([key, task]) => {
                  const config = TASK_CONFIG[key] || {};
                  const Icon = config.icon || Zap;
                  const hourlyEstimate = task.payout_per_task * (3600 / task.avg_time_seconds);
                  
                  return (
                    <Card 
                      key={key}
                      className="p-6 bg-surface/50 border-border/30 hover:border-gold/50 transition-all cursor-pointer"
                      onClick={() => startSession(key)}
                      data-testid={`task-type-${key}`}
                    >
                      <div className="flex items-start gap-4">
                        <div className={`w-14 h-14 rounded-xl ${config.color || 'bg-gray-500'} flex items-center justify-center flex-shrink-0`}>
                          <Icon className="w-7 h-7 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-lg">{task.name}</h3>
                          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{task.description}</p>
                          <div className="flex items-center gap-3 mt-3">
                            <Badge className="bg-gold/20 text-gold">
                              {formatVE(task.payout_per_task)}/task
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              ~{task.avg_time_seconds}s each
                            </span>
                          </div>
                          <div className="text-sm text-green-400 mt-2">
                            ~{formatVE(hourlyEstimate)}/hr estimated
                          </div>
                        </div>
                      </div>
                      <Button className="w-full mt-4 bg-gold text-black hover:bg-gold-light">
                        <Play className="w-4 h-4 mr-2" />
                        Start Session
                      </Button>
                    </Card>
                  );
                })}
              </div>
            </TabsContent>

            <TabsContent value="stats">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Earnings by type */}
                <Card className="p-6 bg-surface/50 border-border/30">
                  <h3 className="font-cinzel text-lg text-gold mb-4">Earnings by Task Type</h3>
                  <div className="space-y-3">
                    {Object.entries(workerStats?.by_task_type || {}).map(([type, data]) => {
                      const config = TASK_CONFIG[type] || {};
                      const Icon = config.icon || Zap;
                      return (
                        <div key={type} className="flex items-center gap-3 p-3 bg-black/20 rounded-lg">
                          <div className={`w-10 h-10 rounded-lg ${config.color || 'bg-gray-500'} flex items-center justify-center`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <div className="font-medium">{config.name || type}</div>
                            <div className="text-sm text-muted-foreground">{data.tasks} tasks</div>
                          </div>
                          <div className="text-gold font-bold">{formatVE(data.earned)}</div>
                        </div>
                      );
                    })}
                    {Object.keys(workerStats?.by_task_type || {}).length === 0 && (
                      <p className="text-center text-muted-foreground py-8">
                        No tasks completed yet. Start earning!
                      </p>
                    )}
                  </div>
                </Card>

                {/* Recent transactions */}
                <Card className="p-6 bg-surface/50 border-border/30">
                  <h3 className="font-cinzel text-lg text-gold mb-4">Recent Earnings</h3>
                  <ScrollArea className="h-[300px]">
                    <div className="space-y-2">
                      {(workerStats?.recent_transactions || []).map((tx, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-black/20 rounded-lg">
                          <div>
                            <div className="font-medium text-sm">{TASK_CONFIG[tx.task_type]?.name || tx.task_type}</div>
                            <div className="text-xs text-muted-foreground">
                              {new Date(tx.timestamp).toLocaleString()}
                            </div>
                          </div>
                          <Badge className="bg-green-500/20 text-green-400">
                            +{formatVE(tx.amount)}
                          </Badge>
                        </div>
                      ))}
                      {(workerStats?.recent_transactions || []).length === 0 && (
                        <p className="text-center text-muted-foreground py-8">
                          No recent transactions
                        </p>
                      )}
                    </div>
                  </ScrollArea>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="leaderboard">
              <Card className="p-6 bg-surface/50 border-border/30">
                <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                  <Trophy className="w-5 h-5" />
                  Hourly Leaderboard
                </h3>
                <div className="space-y-3">
                  {leaderboard.map((entry, idx) => (
                    <div 
                      key={entry._id}
                      className={`flex items-center gap-4 p-4 rounded-lg ${
                        idx === 0 ? 'bg-gold/10 border border-gold/30' :
                        idx === 1 ? 'bg-gray-400/10 border border-gray-400/30' :
                        idx === 2 ? 'bg-amber-600/10 border border-amber-600/30' :
                        'bg-black/20'
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                        idx === 0 ? 'bg-gold text-black' :
                        idx === 1 ? 'bg-gray-400 text-black' :
                        idx === 2 ? 'bg-amber-600 text-black' :
                        'bg-surface text-muted-foreground'
                      }`}>
                        {idx + 1}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">
                          {entry._id === userId ? 'You' : `Worker ${entry._id.slice(-6)}`}
                        </div>
                        <div className="text-sm text-muted-foreground">{entry.tasks} tasks completed</div>
                      </div>
                      <div className="text-xl font-bold text-gold">{formatVE(entry.earned)}</div>
                    </div>
                  ))}
                  {leaderboard.length === 0 && (
                    <p className="text-center text-muted-foreground py-8">
                      No activity in the last hour. Be the first!
                    </p>
                  )}
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
};

export default TasksDashboard;
