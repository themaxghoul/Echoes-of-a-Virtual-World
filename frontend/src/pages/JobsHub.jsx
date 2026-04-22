import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Briefcase, DollarSign, TrendingUp, Users, Clock, Star,
  Play, Square, ChevronRight, ArrowLeft, Sparkles, Brain,
  Hammer, Compass, Shield, BookOpen, Wand2, Handshake,
  Package, Cpu, Award, Zap, Heart, Target
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { pushNavHistory, GameNavigation } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Category icons
const CATEGORY_ICONS = {
  task_work: <Cpu className="w-5 h-5" />,
  data_training: <Brain className="w-5 h-5" />,
  commerce: <DollarSign className="w-5 h-5" />,
  construction: <Hammer className="w-5 h-5" />,
  exploration: <Compass className="w-5 h-5" />,
  diplomacy: <Handshake className="w-5 h-5" />,
  scholarship: <BookOpen className="w-5 h-5" />,
  combat: <Shield className="w-5 h-5" />,
  crafting: <Package className="w-5 h-5" />,
  mysticism: <Wand2 className="w-5 h-5" />
};

const CATEGORY_COLORS = {
  task_work: "text-green-400 bg-green-400/10 border-green-400/30",
  data_training: "text-purple-400 bg-purple-400/10 border-purple-400/30",
  commerce: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  construction: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  exploration: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  diplomacy: "text-pink-400 bg-pink-400/10 border-pink-400/30",
  scholarship: "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
  combat: "text-red-400 bg-red-400/10 border-red-400/30",
  crafting: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  mysticism: "text-violet-400 bg-violet-400/10 border-violet-400/30"
};

const CATEGORY_NAMES = {
  task_work: "Task Work",
  data_training: "AI Training",
  commerce: "Commerce",
  construction: "Construction",
  exploration: "Exploration",
  diplomacy: "Diplomacy",
  scholarship: "Scholarship",
  combat: "Combat",
  crafting: "Crafting",
  mysticism: "Mysticism"
};

const JobsHub = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [jobCatalog, setJobCatalog] = useState({});
  const [myJobs, setMyJobs] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [economyStats, setEconomyStats] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [sessionTimer, setSessionTimer] = useState(0);
  
  const userId = localStorage.getItem('userId');

  useEffect(() => {
    pushNavHistory('/jobs');
    loadData();
  }, []);

  // Session timer
  useEffect(() => {
    let interval;
    if (activeSession && !activeSession.ended_at) {
      interval = setInterval(() => {
        const start = new Date(activeSession.started_at);
        const now = new Date();
        setSessionTimer(Math.floor((now - start) / 1000));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [activeSession]);

  const loadData = async () => {
    try {
      const [catalogRes, myJobsRes, statsRes] = await Promise.all([
        axios.get(`${API}/jobs/catalog`),
        axios.get(`${API}/jobs/player/${userId}`),
        axios.get(`${API}/jobs/economy-stats`)
      ]);
      
      setJobCatalog(catalogRes.data.jobs || {});
      setMyJobs(myJobsRes.data.jobs || []);
      setEconomyStats(statsRes.data);
      
      // Check for active session
      // (Would need endpoint to check active sessions)
    } catch (error) {
      console.error('Failed to load jobs data:', error);
      toast.error('Failed to load jobs');
    }
    setLoading(false);
  };

  const enrollInJob = async (jobKey) => {
    try {
      const res = await axios.post(`${API}/jobs/enroll?player_id=${userId}&job_key=${jobKey}`);
      if (res.data.enrolled) {
        toast.success(res.data.message);
        loadData();
      } else {
        toast.info(res.data.message);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to enroll');
    }
  };

  const startWorkSession = async (jobKey) => {
    try {
      const res = await axios.post(`${API}/jobs/start-work-session?player_id=${userId}&job_key=${jobKey}`);
      if (res.data.started) {
        setActiveSession(res.data);
        setSessionTimer(0);
        toast.success(`Work session started as ${res.data.title}!`);
      } else {
        toast.info(res.data.message);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start session');
    }
  };

  const endWorkSession = async () => {
    if (!activeSession) return;
    
    try {
      const res = await axios.post(`${API}/jobs/end-work-session/${activeSession.session_id}`);
      if (res.data.ended) {
        toast.success(
          `Session complete! Earned VE$${res.data.ve_earned.toFixed(2)} and ${res.data.eco_points_earned} ecosystem points!`,
          { duration: 5000 }
        );
        
        if (res.data.level_up) {
          toast.success(`Level up! You are now a ${res.data.level_up.new_title}!`, { duration: 5000 });
        }
        
        setActiveSession(null);
        setSessionTimer(0);
        loadData();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to end session');
    }
  };

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const isEnrolled = (jobKey) => myJobs.some(j => j.job_key === jobKey);

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian flex items-center justify-center">
        <div className="text-center">
          <Briefcase className="w-16 h-16 mx-auto text-gold animate-pulse mb-4" />
          <p className="font-cinzel text-gold">Loading Jobs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian flex flex-col">
      {/* Background */}
      <div className="fixed inset-0 opacity-20">
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian via-obsidian/90 to-obsidian" />
      </div>

      {/* Navigation */}
      <GameNavigation 
        title="Career Hub" 
        showBack={true} 
        showHome={true} 
        showLogout={true}
      />

      <main className="relative z-10 flex-1 p-4 sm:p-6 overflow-y-auto pb-24">
        {/* Active Session Banner */}
        {activeSession && (
          <Card className="mb-6 bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-green-500/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center animate-pulse">
                    <Briefcase className="w-6 h-6 text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-cinzel text-lg text-green-400">Working as {activeSession.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      Earning VE${activeSession.hourly_rate}/hr + {activeSession.eco_points_rate} eco points/hr
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="font-mono text-2xl text-green-400">{formatTime(sessionTimer)}</p>
                    <p className="text-xs text-muted-foreground">Session Time</p>
                  </div>
                  <Button 
                    onClick={endWorkSession}
                    className="bg-red-600 hover:bg-red-500"
                    data-testid="end-session-btn"
                  >
                    <Square className="w-4 h-4 mr-2" />
                    End Session
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Economy Stats */}
        {economyStats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <Card className="bg-surface/50 border-border/30">
              <CardContent className="p-4 text-center">
                <DollarSign className="w-6 h-6 mx-auto text-green-400 mb-2" />
                <p className="font-mono text-xl text-foreground">
                  VE${economyStats.total_ve_distributed?.toFixed(0) || 0}
                </p>
                <p className="text-xs text-muted-foreground">Total Distributed</p>
              </CardContent>
            </Card>
            <Card className="bg-surface/50 border-border/30">
              <CardContent className="p-4 text-center">
                <Sparkles className="w-6 h-6 mx-auto text-purple-400 mb-2" />
                <p className="font-mono text-xl text-foreground">
                  {economyStats.total_eco_points_generated?.toLocaleString() || 0}
                </p>
                <p className="text-xs text-muted-foreground">Eco Points Generated</p>
              </CardContent>
            </Card>
            <Card className="bg-surface/50 border-border/30">
              <CardContent className="p-4 text-center">
                <Target className="w-6 h-6 mx-auto text-blue-400 mb-2" />
                <p className="font-mono text-xl text-foreground">
                  {economyStats.total_tasks_completed?.toLocaleString() || 0}
                </p>
                <p className="text-xs text-muted-foreground">Tasks Completed</p>
              </CardContent>
            </Card>
            <Card className="bg-surface/50 border-border/30">
              <CardContent className="p-4 text-center">
                <Users className="w-6 h-6 mx-auto text-gold mb-2" />
                <p className="font-mono text-xl text-foreground">
                  {economyStats.unique_workers || 0}
                </p>
                <p className="text-xs text-muted-foreground">Active Workers</p>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="catalog" className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-surface/50 mb-6">
            <TabsTrigger value="catalog" className="font-cinzel">Job Catalog</TabsTrigger>
            <TabsTrigger value="my-jobs" className="font-cinzel">
              My Jobs ({myJobs.length})
            </TabsTrigger>
          </TabsList>

          {/* Job Catalog */}
          <TabsContent value="catalog">
            <div className="space-y-6">
              {Object.entries(jobCatalog).map(([category, jobs]) => (
                <div key={category}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`p-2 rounded-sm ${CATEGORY_COLORS[category]}`}>
                      {CATEGORY_ICONS[category]}
                    </div>
                    <h2 className="font-cinzel text-lg text-foreground">
                      {CATEGORY_NAMES[category] || category}
                    </h2>
                    <Badge className="bg-surface/50 text-muted-foreground">
                      {jobs.length} jobs
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {jobs.map((job) => (
                      <Card 
                        key={job.key}
                        className={`bg-surface/80 border-border/50 hover:border-gold/30 transition-all cursor-pointer ${
                          isEnrolled(job.key) ? 'ring-1 ring-green-500/50' : ''
                        }`}
                        onClick={() => setSelectedJob(job)}
                        data-testid={`job-card-${job.key}`}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <h3 className="font-cinzel text-foreground">{job.name}</h3>
                            {isEnrolled(job.key) && (
                              <Badge className="bg-green-500/20 text-green-400 text-xs">
                                Enrolled
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                            {job.description}
                          </p>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-green-400 font-mono">
                              VE${job.base_hourly_ve}/hr
                            </span>
                            <span className="text-purple-400">
                              +{job.ecosystem_points_per_hour} eco/hr
                            </span>
                          </div>
                          <div className="mt-3 pt-3 border-t border-border/30">
                            <p className="text-xs text-cyan-400 flex items-center gap-1">
                              <Brain className="w-3 h-3" />
                              {job.ai_benefit?.slice(0, 40)}...
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* My Jobs */}
          <TabsContent value="my-jobs">
            {myJobs.length === 0 ? (
              <Card className="bg-surface/50 border-border/30">
                <CardContent className="p-8 text-center">
                  <Briefcase className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-cinzel text-lg text-foreground mb-2">No Jobs Yet</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Browse the catalog and enroll in jobs to start earning VE$ and ecosystem points!
                  </p>
                  <Button 
                    onClick={() => document.querySelector('[value="catalog"]')?.click()}
                    className="bg-gold text-black hover:bg-gold-light"
                  >
                    Browse Jobs
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {myJobs.map((job) => (
                  <Card key={job.job_id} className="bg-surface/80 border-border/50">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-cinzel text-foreground">{job.job_name}</h3>
                          <p className="text-sm text-gold">{job.current_title}</p>
                        </div>
                        <Badge className={`${CATEGORY_COLORS[job.category]}`}>
                          Lvl {job.current_level}
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <p className="text-xs text-muted-foreground">Total Earned</p>
                          <p className="font-mono text-green-400">VE${job.total_ve_earned?.toFixed(2) || 0}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Eco Points</p>
                          <p className="font-mono text-purple-400">{job.total_eco_points || 0}</p>
                        </div>
                      </div>
                      
                      <div className="mb-4">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted-foreground">Experience</span>
                          <span className="text-gold">{job.experience || 0} XP</span>
                        </div>
                        <Progress value={Math.min(100, (job.experience || 0) / 10)} className="h-2" />
                      </div>
                      
                      <div className="flex gap-2">
                        {!activeSession ? (
                          <Button 
                            onClick={() => startWorkSession(job.job_key)}
                            className="flex-1 bg-green-600 hover:bg-green-500"
                            data-testid={`start-work-${job.job_key}`}
                          >
                            <Play className="w-4 h-4 mr-2" />
                            Start Working
                          </Button>
                        ) : activeSession.job_key === job.job_key ? (
                          <Button 
                            onClick={endWorkSession}
                            className="flex-1 bg-red-600 hover:bg-red-500"
                          >
                            <Square className="w-4 h-4 mr-2" />
                            End Session
                          </Button>
                        ) : (
                          <Button 
                            disabled
                            className="flex-1"
                          >
                            In Different Session
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Selected Job Modal */}
        {selectedJob && (
          <div 
            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedJob(null)}
          >
            <Card 
              className="bg-surface border-border/50 max-w-lg w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader className="border-b border-border/30">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="font-cinzel text-gold">{selectedJob.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Level {selectedJob.requirements?.level || 1} required
                    </p>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={() => setSelectedJob(null)}
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <p className="text-foreground">{selectedJob.description}</p>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-green-500/10 rounded-sm">
                    <p className="text-xs text-green-400 mb-1">Hourly Rate</p>
                    <p className="font-mono text-xl text-green-400">VE${selectedJob.base_hourly_ve}</p>
                  </div>
                  <div className="p-3 bg-purple-500/10 rounded-sm">
                    <p className="text-xs text-purple-400 mb-1">Eco Points/hr</p>
                    <p className="font-mono text-xl text-purple-400">+{selectedJob.ecosystem_points_per_hour}</p>
                  </div>
                </div>
                
                <div className="p-3 bg-cyan-500/10 rounded-sm">
                  <p className="text-xs text-cyan-400 mb-1 flex items-center gap-1">
                    <Brain className="w-3 h-3" />
                    AI Benefit
                  </p>
                  <p className="text-sm text-cyan-300">{selectedJob.ai_benefit}</p>
                </div>
                
                <div className="pt-4 border-t border-border/30">
                  {isEnrolled(selectedJob.key) ? (
                    <div className="space-y-3">
                      <Badge className="bg-green-500/20 text-green-400 w-full justify-center py-2">
                        Already Enrolled
                      </Badge>
                      {!activeSession && (
                        <Button 
                          onClick={() => {
                            startWorkSession(selectedJob.key);
                            setSelectedJob(null);
                          }}
                          className="w-full bg-green-600 hover:bg-green-500"
                        >
                          <Play className="w-4 h-4 mr-2" />
                          Start Working Now
                        </Button>
                      )}
                    </div>
                  ) : (
                    <Button 
                      onClick={() => {
                        enrollInJob(selectedJob.key);
                        setSelectedJob(null);
                      }}
                      className="w-full bg-gold text-black hover:bg-gold-light"
                      data-testid="enroll-job-btn"
                    >
                      <Briefcase className="w-4 h-4 mr-2" />
                      Enroll in This Job
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-obsidian/90 backdrop-blur-sm border-t border-border/30 p-3 z-40">
        <div className="flex justify-center gap-3 max-w-lg mx-auto">
          <Button
            variant="outline"
            onClick={() => navigate('/earnings')}
            className="flex-1 border-green-500/30 text-green-400"
          >
            <DollarSign className="w-4 h-4 mr-2" />
            VE$ Balance
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate('/select-mode')}
            className="flex-1 border-gold/30 text-gold"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Play Game
          </Button>
        </div>
      </div>
    </div>
  );
};

export default JobsHub;
