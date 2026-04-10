import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Wallet, DollarSign, TrendingUp, Clock, CheckCircle, 
  AlertTriangle, ArrowUpRight, ArrowDownLeft, RefreshCw,
  Briefcase, FileText, Mic, BarChart3, Cpu, Users,
  Link2, ExternalLink, Play, Pause, Settings, Star,
  ArrowLeft, Zap, Target, Award, Globe
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Virtual Echo Dollar formatting
const formatVE = (amount) => {
  if (amount === null || amount === undefined) return 'VE$0.00';
  return `VE$${parseFloat(amount).toFixed(2)}`;
};

const formatUSD = (amount) => {
  if (amount === null || amount === undefined) return '$0.00';
  return `$${parseFloat(amount).toFixed(2)}`;
};

// Income stream icons
const STREAM_ICONS = {
  micro_tasks: Briefcase,
  data_labeling: FileText,
  transcription: Mic,
  surveys: BarChart3,
  compute_share: Cpu,
  affiliate: Users,
  crypto_staking: TrendingUp,
  blockchain_solve: Link2,
};

const STREAM_COLORS = {
  micro_tasks: 'bg-blue-500',
  data_labeling: 'bg-purple-500',
  transcription: 'bg-green-500',
  surveys: 'bg-yellow-500',
  compute_share: 'bg-cyan-500',
  affiliate: 'bg-pink-500',
  crypto_staking: 'bg-orange-500',
  blockchain_solve: 'bg-indigo-500',
};

const EarningsHub = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  
  // Account state
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [incomeStreams, setIncomeStreams] = useState({});
  
  // Wallet state
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [walletBalance, setWalletBalance] = useState({});
  
  // Tasks state
  const [availableTasks, setAvailableTasks] = useState([]);
  const [activeTask, setActiveTask] = useState(null);
  const [taskTimer, setTaskTimer] = useState(0);
  
  // Withdrawal state
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawPreview, setWithdrawPreview] = useState(null);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  
  // Stats
  const [todayEarnings, setTodayEarnings] = useState(0);
  const [weeklyEarnings, setWeeklyEarnings] = useState(0);
  const [hourlyRate, setHourlyRate] = useState(0);
  
  // Ecosystem state
  const [ecosystemStatus, setEcosystemStatus] = useState(null);
  const [userContributions, setUserContributions] = useState(null);
  const [activeTab, setActiveTab] = useState('tasks');
  
  // Deposit state
  const [depositAmount, setDepositAmount] = useState('');
  const [depositLoading, setDepositLoading] = useState(false);
  
  // Load account data
  const loadAccount = useCallback(async () => {
    if (!userId) {
      toast.error('Please login first');
      navigate('/auth');
      return;
    }
    
    setLoading(true);
    try {
      const [accountRes, streamsRes, tasksRes] = await Promise.all([
        axios.get(`${API}/earnings/account/${userId}`),
        axios.get(`${API}/earnings/income-streams`),
        axios.get(`${API}/earnings/tasks/available?user_id=${userId}&limit=10`).catch(() => ({ data: { tasks: [] } }))
      ]);
      
      setAccount(accountRes.data);
      setIncomeStreams(streamsRes.data.streams || {});
      setAvailableTasks(tasksRes.data.tasks || []);
      
      // Calculate stats
      const totalEarned = accountRes.data.total_earned_usd || 0;
      const tasksCompleted = accountRes.data.tasks_completed || 0;
      setHourlyRate(tasksCompleted > 0 ? (totalEarned / (tasksCompleted * 0.1)).toFixed(2) : 0);
      setTodayEarnings(totalEarned * 0.1); // Simulated
      setWeeklyEarnings(totalEarned * 0.5); // Simulated
      
      // Check wallet
      if (accountRes.data.connected_wallets?.length > 0) {
        setWalletConnected(true);
        setWalletAddress(accountRes.data.primary_wallet || accountRes.data.connected_wallets[0]);
      }
    } catch (error) {
      console.error('Failed to load account:', error);
      toast.error('Failed to load earnings data');
    }
    setLoading(false);
  }, [userId, navigate]);
  
  // Load ecosystem data
  const loadEcosystem = useCallback(async () => {
    try {
      const [statusRes, userRes] = await Promise.all([
        axios.get(`${API}/ecosystem/status`),
        axios.get(`${API}/ecosystem/user/${userId}`).catch(() => ({ data: null }))
      ]);
      setEcosystemStatus(statusRes.data);
      setUserContributions(userRes.data);
    } catch (error) {
      console.error('Failed to load ecosystem:', error);
    }
  }, [userId]);
  
  useEffect(() => {
    loadAccount();
    loadEcosystem();
  }, [loadAccount, loadEcosystem]);
  
  // Task timer
  useEffect(() => {
    let interval;
    if (activeTask) {
      interval = setInterval(() => {
        setTaskTimer(t => t + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [activeTask]);
  
  // Connect wallet (Web3)
  const connectWallet = async () => {
    if (typeof window.ethereum === 'undefined') {
      toast.error('MetaMask not detected. Please install MetaMask to connect your wallet.');
      window.open('https://metamask.io/download/', '_blank');
      return;
    }
    
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const address = accounts[0];
      
      // Save to backend
      await axios.post(`${API}/earnings/wallet/connect?user_id=${userId}&wallet_address=${address}&network=polygon`);
      
      setWalletConnected(true);
      setWalletAddress(address);
      toast.success('Wallet connected successfully!');
      
      // Get balance
      const balance = await window.ethereum.request({
        method: 'eth_getBalance',
        params: [address, 'latest']
      });
      const ethBalance = parseInt(balance, 16) / 1e18;
      setWalletBalance({ ETH: ethBalance.toFixed(4) });
      
    } catch (error) {
      console.error('Wallet connection failed:', error);
      toast.error('Failed to connect wallet');
    }
  };
  
  // Accept task
  const acceptTask = async (task) => {
    try {
      const res = await axios.post(`${API}/earnings/tasks/${task.task_id}/accept?user_id=${userId}`);
      setActiveTask({ ...task, ...res.data });
      setTaskTimer(0);
      toast.success(`Task accepted: ${task.title}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept task');
    }
  };
  
  // Submit task
  const submitTask = async () => {
    if (!activeTask) return;
    
    try {
      const res = await axios.post(`${API}/earnings/tasks/${activeTask.task_id}/submit`, {
        task_id: activeTask.task_id,
        user_id: userId,
        submission_data: { completed: true, quality: 'good' },
        time_taken_seconds: taskTimer
      });
      
      toast.success(`Task completed! Earned ${formatVE(res.data.reward_usd)}`);
      setActiveTask(null);
      setTaskTimer(0);
      loadAccount(); // Refresh
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit task');
    }
  };
  
  // Preview withdrawal
  const previewWithdrawal = async () => {
    const amount = parseFloat(withdrawAmount);
    if (isNaN(amount) || amount < 1) {
      toast.error('Minimum withdrawal is VE$1.00');
      return;
    }
    
    try {
      const res = await axios.get(`${API}/earnings/withdraw/preview/${userId}?amount=${amount}`);
      setWithdrawPreview(res.data);
      setShowWithdrawModal(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to preview withdrawal');
    }
  };
  
  // Process withdrawal
  const processWithdrawal = async (destinationType) => {
    try {
      // Create withdrawal request
      const withdrawRes = await axios.post(`${API}/earnings/withdraw`, {
        user_id: userId,
        amount_usd: parseFloat(withdrawAmount),
        method: destinationType === 'wallet' ? 'crypto' : 'game_balance',
        destination: destinationType === 'wallet' ? walletAddress : 'game_balance'
      });
      
      // Set destination
      await axios.post(`${API}/earnings/withdraw/set-destination`, {
        user_id: userId,
        withdrawal_id: withdrawRes.data.withdrawal_id,
        destination_type: destinationType,
        wallet_address: destinationType === 'wallet' ? walletAddress : null,
        wallet_percentage: destinationType === 'wallet' ? 100 : 0
      });
      
      toast.success(`Withdrawal of ${formatVE(withdrawAmount)} initiated!`);
      setShowWithdrawModal(false);
      setWithdrawAmount('');
      loadAccount();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Withdrawal failed');
    }
  };
  
  // Deposit VE$ via Stripe
  const initiateDeposit = async () => {
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount < 1) {
      toast.error('Minimum deposit is $1.00');
      return;
    }
    
    setDepositLoading(true);
    try {
      const res = await axios.post(`${API}/payments/deposit/checkout`, {
        user_id: userId,
        amount: amount,
        origin_url: window.location.origin,
        payment_methods: ['card']
      });
      
      // Redirect to Stripe checkout
      window.location.href = res.data.checkout_url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate deposit');
      setDepositLoading(false);
    }
  };
  
  // Check for returning from Stripe
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    const status = urlParams.get('status');
    
    if (sessionId && status === 'success') {
      // Poll for payment status
      const pollStatus = async (attempts = 0) => {
        if (attempts >= 5) {
          toast.info('Payment processing. Balance will update shortly.');
          return;
        }
        
        try {
          const res = await axios.get(`${API}/payments/deposit/status/${sessionId}`);
          if (res.data.payment_status === 'paid') {
            toast.success('Deposit successful! VE$ credited to your account.');
            loadAccount();
            window.history.replaceState({}, '', '/earnings');
          } else if (res.data.status === 'expired') {
            toast.error('Payment session expired.');
            window.history.replaceState({}, '', '/earnings');
          } else {
            setTimeout(() => pollStatus(attempts + 1), 2000);
          }
        } catch (error) {
          console.error('Status check error:', error);
        }
      };
      
      pollStatus();
    } else if (status === 'cancelled') {
      toast.info('Payment cancelled');
      window.history.replaceState({}, '', '/earnings');
    }
  }, []);
  
  // Support ecosystem
  const supportEcosystem = async (supportAmount) => {
    if (supportAmount > (account?.available_balance_usd || 0)) {
      toast.error('Insufficient VE$ balance');
      return;
    }
    
    try {
      const res = await axios.post(`${API}/ecosystem/support`, {
        user_id: userId,
        support_type: 'direct',
        amount_ve: supportAmount
      });
      
      toast.success(res.data.message);
      loadAccount();
      loadEcosystem();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Support failed');
    }
  };
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gold animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Earnings Hub...</p>
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
            <Button variant="ghost" size="icon" onClick={() => navigate('/play')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Zap className="w-6 h-6" />
                Earnings Hub
              </h1>
              <p className="text-sm text-muted-foreground">ApexForge Collective</p>
            </div>
          </div>
          
          {/* Wallet Connection */}
          <div className="flex items-center gap-4">
            {walletConnected ? (
              <div className="flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-lg">
                <Wallet className="w-4 h-4 text-green-500" />
                <span className="text-sm font-mono text-green-400">
                  {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
                </span>
                <Badge className="bg-green-500/20 text-green-400">Connected</Badge>
              </div>
            ) : (
              <Button onClick={connectWallet} className="bg-purple-600 hover:bg-purple-500">
                <Wallet className="w-4 h-4 mr-2" />
                Connect Wallet
              </Button>
            )}
          </div>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto p-4 space-y-6">
        {/* Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Total Balance */}
          <Card className="p-6 bg-gradient-to-br from-gold/20 to-gold/5 border-gold/30">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="w-8 h-8 text-gold" />
              <Badge className="bg-gold/20 text-gold">VE$</Badge>
            </div>
            <div className="text-3xl font-bold text-gold mb-1">
              {formatVE(account?.available_balance_usd || 0)}
            </div>
            <p className="text-sm text-muted-foreground">Available Balance</p>
            <p className="text-xs text-gold/60 mt-2">
              ≈ {formatUSD(account?.available_balance_usd || 0)} USD
            </p>
          </Card>
          
          {/* Today's Earnings */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-6 h-6 text-green-500" />
              <Badge className="bg-green-500/20 text-green-400">Today</Badge>
            </div>
            <div className="text-2xl font-bold text-foreground mb-1">
              {formatVE(todayEarnings)}
            </div>
            <p className="text-sm text-muted-foreground">Earned Today</p>
          </Card>
          
          {/* Hourly Rate */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <div className="flex items-center justify-between mb-4">
              <Clock className="w-6 h-6 text-blue-500" />
              <Badge className="bg-blue-500/20 text-blue-400">Rate</Badge>
            </div>
            <div className="text-2xl font-bold text-foreground mb-1">
              {formatVE(hourlyRate)}/hr
            </div>
            <p className="text-sm text-muted-foreground">Average Hourly</p>
          </Card>
          
          {/* Tasks Completed */}
          <Card className="p-6 bg-surface/50 border-border/30">
            <div className="flex items-center justify-between mb-4">
              <CheckCircle className="w-6 h-6 text-purple-500" />
              <Badge className="bg-purple-500/20 text-purple-400">Tasks</Badge>
            </div>
            <div className="text-2xl font-bold text-foreground mb-1">
              {account?.tasks_completed || 0}
            </div>
            <p className="text-sm text-muted-foreground">Completed</p>
          </Card>
        </div>
        
        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tasks Panel */}
          <div className="lg:col-span-2">
            <Card className="bg-surface/50 border-border/30">
              <div className="p-4 border-b border-border/30 flex items-center justify-between">
                <h2 className="font-cinzel text-lg text-gold flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  Available Tasks
                </h2>
                <Button variant="ghost" size="sm" onClick={loadAccount}>
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
              
              {/* Active Task */}
              {activeTask && (
                <div className="p-4 bg-gold/10 border-b border-gold/30">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Play className="w-5 h-5 text-gold animate-pulse" />
                      <span className="font-medium text-gold">Active Task</span>
                    </div>
                    <Badge className="bg-gold text-black">{formatTime(taskTimer)}</Badge>
                  </div>
                  <h3 className="font-medium mb-2">{activeTask.title}</h3>
                  <p className="text-sm text-muted-foreground mb-4">{activeTask.description}</p>
                  <div className="flex items-center gap-3">
                    <Button onClick={submitTask} className="bg-green-600 hover:bg-green-500">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Complete Task ({formatVE(activeTask.reward_usd)})
                    </Button>
                    <Button variant="outline" onClick={() => setActiveTask(null)}>
                      <Pause className="w-4 h-4 mr-2" />
                      Abandon
                    </Button>
                  </div>
                </div>
              )}
              
              {/* Task List */}
              <ScrollArea className="h-[400px]">
                <div className="p-4 space-y-3">
                  {availableTasks.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No tasks available right now</p>
                      <p className="text-sm">Check back soon!</p>
                    </div>
                  ) : (
                    availableTasks.map(task => {
                      const Icon = STREAM_ICONS[task.task_type] || Briefcase;
                      const color = STREAM_COLORS[task.task_type] || 'bg-gray-500';
                      
                      return (
                        <Card 
                          key={task.task_id}
                          className="p-4 bg-obsidian/50 border-border/30 hover:border-gold/30 transition-colors"
                        >
                          <div className="flex items-start gap-4">
                            <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
                              <Icon className="w-5 h-5 text-white" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <h3 className="font-medium">{task.title}</h3>
                                <span className="text-lg font-bold text-gold">{formatVE(task.reward_usd)}</span>
                              </div>
                              <p className="text-sm text-muted-foreground mt-1">{task.description}</p>
                              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  ~{task.time_estimate_minutes} min
                                </span>
                                <Badge variant="outline" className="text-xs">
                                  {task.difficulty}
                                </Badge>
                              </div>
                            </div>
                            <Button 
                              size="sm" 
                              onClick={() => acceptTask(task)}
                              disabled={!!activeTask}
                              className="bg-gold text-black hover:bg-gold-light"
                            >
                              Start
                            </Button>
                          </div>
                        </Card>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            </Card>
          </div>
          
          {/* Right Panel */}
          <div className="space-y-6">
            {/* Deposit Card */}
            <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-500/30">
              <h3 className="font-cinzel text-lg text-green-400 mb-4 flex items-center gap-2">
                <ArrowDownLeft className="w-5 h-5" />
                Buy VE$
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground mb-2 block">Amount (USD)</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-green-400 font-bold">$</span>
                    <Input 
                      type="number"
                      value={depositAmount}
                      onChange={(e) => setDepositAmount(e.target.value)}
                      placeholder="10.00"
                      className="pl-8 bg-obsidian border-green-500/30"
                      min="1"
                      step="0.01"
                      data-testid="deposit-amount-input"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    1 USD = 1 VE$ | Instant credit
                  </p>
                </div>
                
                <Button 
                  onClick={initiateDeposit}
                  className="w-full bg-green-600 hover:bg-green-500"
                  disabled={depositLoading || !depositAmount || parseFloat(depositAmount) < 1}
                  data-testid="deposit-btn"
                >
                  {depositLoading ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <DollarSign className="w-4 h-4 mr-2" />
                  )}
                  {depositLoading ? 'Processing...' : 'Buy VE$ with Card'}
                </Button>
              </div>
            </Card>
            
            {/* Withdrawal Card */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5" />
                Withdraw Funds
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground mb-2 block">Amount (VE$)</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gold font-bold">VE$</span>
                    <Input 
                      type="number"
                      value={withdrawAmount}
                      onChange={(e) => setWithdrawAmount(e.target.value)}
                      placeholder="0.00"
                      className="pl-12 bg-obsidian border-border/50"
                      min="1"
                      step="0.01"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Min: VE$1.00 | Fee: VE$0.25 | Available: {formatVE(account?.available_balance_usd)}
                  </p>
                </div>
                
                <Button 
                  onClick={previewWithdrawal}
                  className="w-full bg-gold text-black hover:bg-gold-light"
                  disabled={!withdrawAmount || parseFloat(withdrawAmount) < 1}
                >
                  Preview Withdrawal
                </Button>
              </div>
            </Card>
            
            {/* Income Streams */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <Star className="w-5 h-5" />
                Income Streams
              </h3>
              
              <div className="space-y-3">
                {Object.entries(incomeStreams).slice(0, 5).map(([key, stream]) => {
                  const Icon = STREAM_ICONS[key] || Briefcase;
                  const color = STREAM_COLORS[key] || 'bg-gray-500';
                  
                  return (
                    <div 
                      key={key}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                    >
                      <div className={`w-8 h-8 rounded ${color} flex items-center justify-center`}>
                        <Icon className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{stream.name}</p>
                        <p className="text-xs text-muted-foreground">{stream.avg_hourly_rate}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
            
            {/* Quick Stats */}
            <Card className="p-6 bg-surface/50 border-border/30">
              <h3 className="font-cinzel text-lg text-gold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Performance
              </h3>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Total Earned</span>
                    <span className="text-gold">{formatVE(account?.total_earned_usd)}</span>
                  </div>
                  <Progress value={Math.min(100, (account?.total_earned_usd || 0) * 10)} className="h-2" />
                </div>
                
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Withdrawn</span>
                    <span>{formatVE(account?.total_withdrawn_usd)}</span>
                  </div>
                  <Progress value={Math.min(100, (account?.total_withdrawn_usd || 0) * 10)} className="h-2" />
                </div>
                
                <div className="pt-2 border-t border-border/30">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Pending</span>
                    <span className="text-yellow-400">{formatVE(account?.pending_balance_usd)}</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
        
        {/* Ecosystem Support Section */}
        {ecosystemStatus && (
          <Card className="p-6 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-cyan-500/10 border-purple-500/30">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h3 className="font-cinzel text-xl text-purple-400 flex items-center gap-2">
                  <Cpu className="w-6 h-6" />
                  Ecosystem Support
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Help develop the AI and advance technology tiers
                </p>
              </div>
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Current Tier</div>
                <div className="text-lg font-bold text-purple-400">
                  {ecosystemStatus.technology_tier?.name || 'Primitive'}
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-black/30 rounded-lg">
                <div className="text-sm text-muted-foreground">Total Contributions</div>
                <div className="text-2xl font-bold text-foreground">
                  {ecosystemStatus.ecosystem?.total_contribution_points?.toLocaleString() || 0}
                </div>
              </div>
              <div className="p-4 bg-black/30 rounded-lg">
                <div className="text-sm text-muted-foreground">AI Intelligence</div>
                <div className="text-2xl font-bold text-cyan-400 capitalize">
                  {ecosystemStatus.ai_intelligence?.name || 'Dormant'}
                </div>
              </div>
              <div className="p-4 bg-black/30 rounded-lg">
                <div className="text-sm text-muted-foreground">Your Contributions</div>
                <div className="text-2xl font-bold text-purple-400">
                  {userContributions?.stats?.total_points?.toLocaleString() || 0}
                </div>
                <div className="text-xs text-muted-foreground">
                  Rank #{userContributions?.rank || '—'} • {userContributions?.tier || 'Newcomer'}
                </div>
              </div>
            </div>
            
            {/* Progress to next tier */}
            {ecosystemStatus.technology_tier?.next_tier_name && (
              <div className="mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-muted-foreground">Progress to {ecosystemStatus.technology_tier.next_tier_name}</span>
                  <span className="text-purple-400">{ecosystemStatus.technology_tier.progress_to_next}%</span>
                </div>
                <Progress value={ecosystemStatus.technology_tier.progress_to_next} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {ecosystemStatus.technology_tier.points_to_next_tier.toLocaleString()} points needed
                </p>
              </div>
            )}
            
            {/* Support buttons */}
            <div className="flex flex-wrap gap-3">
              <Button 
                onClick={() => supportEcosystem(1)}
                className="bg-purple-600 hover:bg-purple-500"
                disabled={(account?.available_balance_usd || 0) < 1}
                data-testid="support-1ve-btn"
              >
                Support VE$1 (+10 pts)
              </Button>
              <Button 
                onClick={() => supportEcosystem(5)}
                className="bg-purple-600 hover:bg-purple-500"
                disabled={(account?.available_balance_usd || 0) < 5}
              >
                Support VE$5 (+50 pts)
              </Button>
              <Button 
                onClick={() => supportEcosystem(10)}
                className="bg-purple-600 hover:bg-purple-500"
                disabled={(account?.available_balance_usd || 0) < 10}
              >
                Support VE$10 (+100 pts)
              </Button>
            </div>
            
            <p className="text-xs text-muted-foreground mt-4">
              Your support helps advance AI intelligence and unlock new game features for everyone.
            </p>
          </Card>
        )}
        
        {/* VE Dollar Info */}
        <Card className="p-4 bg-gold/5 border-gold/20">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-gold/20 flex items-center justify-center">
              <span className="text-2xl font-bold text-gold">VE</span>
            </div>
            <div>
              <h3 className="font-cinzel text-gold">Virtual Echo Dollar (VE$)</h3>
              <p className="text-sm text-muted-foreground">
                1 VE$ = 1 USD | Earn in-game, withdraw to real wallet | Powered by ApexForge Collective
              </p>
            </div>
            <Button variant="outline" className="ml-auto" onClick={() => navigate('/terms')}>
              <Globe className="w-4 h-4 mr-2" />
              Terms
            </Button>
          </div>
        </Card>
      </div>
      
      {/* Withdrawal Modal */}
      {showWithdrawModal && withdrawPreview && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md bg-surface border-border/30">
            <div className="p-6">
              <h2 className="font-cinzel text-xl text-gold mb-6">Confirm Withdrawal</h2>
              
              <div className="space-y-4 mb-6">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Amount</span>
                  <span className="font-bold">{formatVE(withdrawPreview.amount_requested)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Processing Fee</span>
                  <span className="text-yellow-400">-{formatVE(withdrawPreview.withdrawal_fee)}</span>
                </div>
                <div className="border-t border-border/30 pt-2 flex justify-between">
                  <span className="font-medium">Total Deduction</span>
                  <span className="font-bold text-gold">{formatVE(withdrawPreview.total_deduction)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Remaining Balance</span>
                  <span>{formatVE(withdrawPreview.remaining_after_withdrawal)}</span>
                </div>
              </div>
              
              <p className="text-sm text-muted-foreground mb-4">Where should we send your funds?</p>
              
              <div className="space-y-3">
                {walletConnected && (
                  <Button 
                    onClick={() => processWithdrawal('wallet')}
                    className="w-full bg-purple-600 hover:bg-purple-500 justify-start"
                  >
                    <Wallet className="w-4 h-4 mr-3" />
                    <div className="text-left">
                      <div>Send to Wallet</div>
                      <div className="text-xs opacity-70">{walletAddress.slice(0, 10)}...{walletAddress.slice(-6)}</div>
                    </div>
                  </Button>
                )}
                
                <Button 
                  onClick={() => processWithdrawal('game_balance')}
                  className="w-full bg-gold text-black hover:bg-gold-light justify-start"
                >
                  <DollarSign className="w-4 h-4 mr-3" />
                  <div className="text-left">
                    <div>Keep in Game Balance</div>
                    <div className="text-xs opacity-70">Use for in-game purchases</div>
                  </div>
                </Button>
                
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => setShowWithdrawModal(false)}
                >
                  Cancel
                </Button>
              </div>
              
              <p className="text-xs text-muted-foreground text-center mt-4">
                Processing time: 1-3 business days
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default EarningsHub;
