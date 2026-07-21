// Field Ops — DoorDash Tasks.app-style real-world capture missions.
// Three op types: Photo, Voice, Video. Optional geo-bonus when on-site.

import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Camera, Mic, Video, MapPin, Clock, CheckCircle2, XCircle,
  Loader2, ArrowLeft, DollarSign, AlertTriangle, Sparkles, ChevronRight,
  Play, Square, RotateCcw, Send, ShieldCheck, Filter
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { pushNavHistory } from '@/components/GameNavigation';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const ICON_BY_TYPE = { photo: Camera, voice: Mic, video: Video };
const COLOR_BY_TYPE = { photo: 'text-amber-400', voice: 'text-emerald-400', video: 'text-fuchsia-400' };
const BORDER_BY_TYPE = { photo: 'border-amber-400/30', voice: 'border-emerald-400/30', video: 'border-fuchsia-400/30' };
const STATUS_STYLE = {
  approved: 'text-emerald-400 border-emerald-400/40',
  auto_approved: 'text-emerald-400 border-emerald-400/40',
  queued_review: 'text-amber-300 border-amber-400/40',
  accepted: 'text-cyan-300 border-cyan-400/40',
  in_progress: 'text-cyan-300 border-cyan-400/40',
  auto_rejected: 'text-rose-400 border-rose-400/40',
  rejected: 'text-rose-400 border-rose-400/40',
};

const SubmissionRow = ({ sub }) => {
  const Icon = ICON_BY_TYPE[sub.op_type] || Camera;
  const statusStyle = STATUS_STYLE[sub.status] || 'text-muted-foreground border-border/30';
  const iconColor = COLOR_BY_TYPE[sub.op_type] || '';
  const when = new Date(sub.accepted_at || sub.submitted_at || Date.now()).toLocaleString();
  return (
    <Card className="bg-surface/40 border-border/30 rounded-sm">
      <CardContent className="p-3 flex items-center gap-3">
        <Icon className={`w-4 h-4 ${iconColor}`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate">{sub.op_title}</p>
          <p className="text-[10px] text-muted-foreground font-mono">{when}</p>
        </div>
        <Badge variant="outline" className={`text-[10px] ${statusStyle}`}>{sub.status}</Badge>
        {sub.paid_ve > 0 && (
          <span className="font-mono text-xs text-emerald-400">+VE${sub.paid_ve.toFixed(2)}</span>
        )}
      </CardContent>
    </Card>
  );
};

const fileToBase64 = (blob) => new Promise((resolve, reject) => {
  const r = new FileReader();
  r.onloadend = () => resolve(r.result);
  r.onerror = reject;
  r.readAsDataURL(blob);
});

const FieldOps = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');

  const [ops, setOps] = useState([]);
  const [walletBalance, setWalletBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('all');
  const [geoEnabled, setGeoEnabled] = useState(false);
  const [geo, setGeo] = useState(null);
  const [activeOp, setActiveOp] = useState(null);
  const [submissionId, setSubmissionId] = useState(null);
  const [captureBlob, setCaptureBlob] = useState(null);
  const [captureMime, setCaptureMime] = useState(null);
  const [captureDurationMs, setCaptureDurationMs] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [resultModal, setResultModal] = useState(null);
  const [tab, setTab] = useState('available');
  const [history, setHistory] = useState([]);

  const loadOps = useCallback(async (coords = null) => {
    try {
      const params = {};
      if (coords) { params.lat = coords.lat; params.lng = coords.lng; }
      if (userId) params.user_id = userId;
      const { data } = await axios.get(`${API}/field-ops/available`, { params });
      setOps(data.ops || []);
    } catch {
      toast.error('Failed to load Field Ops');
    }
  }, [userId]);

  const loadWallet = useCallback(async () => {
    if (!userId) return;
    try {
      const { data } = await axios.get(`${API}/cosmetics/wallet/${userId}`);
      setWalletBalance(data.balance_ve || 0);
    } catch { /* non-fatal */ }
  }, [userId]);

  const loadHistory = useCallback(async () => {
    if (!userId) return;
    try {
      const { data } = await axios.get(`${API}/field-ops/my-submissions/${userId}`);
      setHistory(data.submissions || []);
    } catch { /* non-fatal */ }
  }, [userId]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([loadOps(), loadWallet(), loadHistory()]);
    setLoading(false);
  }, [loadOps, loadWallet, loadHistory]);

  useEffect(() => {
    pushNavHistory('/field-ops');
    if (!userId) {
      navigate('/auth');
      return;
    }
    loadAll();
  }, [userId, navigate, loadAll]);

  const handleGeoToggle = useCallback((enabled) => {
    setGeoEnabled(enabled);
    if (!enabled) {
      setGeo(null);
      loadOps();
      return;
    }
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported on this device');
      setGeoEnabled(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setGeo(coords);
        toast.success('Location locked. Geo bonuses unlocked.');
        loadOps(coords);
      },
      (err) => {
        toast.error(`Location denied: ${err.message}`);
        setGeoEnabled(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, [loadOps]);

  const acceptOp = useCallback(async (op) => {
    try {
      const { data } = await axios.post(`${API}/field-ops/accept`, { user_id: userId, op_id: op.op_id });
      setSubmissionId(data.submission_id);
      setActiveOp(op);
      setCaptureBlob(null);
      setPreviewUrl(null);
      setCaptureMime(null);
      setCaptureDurationMs(null);
      setNotes('');
      toast.success(`Op accepted — locked for 30 min`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not accept op');
    }
  }, [userId]);

  const submitOp = useCallback(async () => {
    if (!captureBlob || !captureMime) return;
    setSubmitting(true);
    try {
      const b64 = await fileToBase64(captureBlob);
      const payload = {
        user_id: userId,
        submission_id: submissionId,
        media_base64: b64,
        mime_type: captureMime,
        duration_ms: captureDurationMs,
        lat: geo?.lat,
        lng: geo?.lng,
        notes: notes || null,
      };
      const { data } = await axios.post(`${API}/field-ops/submit`, payload);
      setResultModal({ ...data, opTitle: activeOp.title });
      setActiveOp(null);
      setSubmissionId(null);
      setCaptureBlob(null);
      setPreviewUrl(null);
      await Promise.all([loadOps(geo), loadWallet(), loadHistory()]);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  }, [captureBlob, captureMime, userId, submissionId, captureDurationMs, geo, notes, activeOp, loadOps, loadWallet, loadHistory]);

  const filteredOps = ops.filter(o => filterType === 'all' || o.type === filterType);

  return (
    <div className="min-h-screen bg-obsidian text-foreground" data-testid="field-ops-page">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-obsidian/90 backdrop-blur-md border-b border-border/30">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <button
            onClick={() => navigate('/economy')}
            className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition"
            data-testid="field-ops-back-btn"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-cinzel text-sm hidden sm:inline">Economy</span>
          </button>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h1 className="font-cinzel text-lg sm:text-xl tracking-wide">Field Ops</h1>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-sm">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            <span className="font-mono text-sm text-emerald-300" data-testid="field-ops-balance">{walletBalance.toFixed(2)}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Intro card */}
        <Card className="bg-gradient-to-br from-amber-500/5 to-fuchsia-500/5 border-amber-500/20 rounded-sm mb-5">
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-6 h-6 text-amber-400 mt-0.5 shrink-0" />
              <div className="flex-1">
                <h2 className="font-cinzel text-base sm:text-lg mb-1">Real-world ops, real VE$</h2>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                  Capture photos, record voice, or film short videos. Submit instantly — AI quality-checks small ops
                  for auto-pay; high-value ops route to human review. Enable location for <span className="text-emerald-400">+20% bonus</span> when you&apos;re on-site.
                </p>
                <div className="flex items-center gap-3 mt-3 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Switch checked={geoEnabled} onCheckedChange={handleGeoToggle} data-testid="field-ops-geo-toggle" />
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <MapPin className="w-3.5 h-3.5" /> Use my location
                    </span>
                  </label>
                  {geo && <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 text-[10px]">
                    {geo.lat.toFixed(3)}, {geo.lng.toFixed(3)}
                  </Badge>}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList className="bg-surface/60 border border-border/30 rounded-sm">
            <TabsTrigger value="available" data-testid="field-ops-tab-available">Available ({filteredOps.length})</TabsTrigger>
            <TabsTrigger value="history" data-testid="field-ops-tab-history">My Submissions ({history.length})</TabsTrigger>
          </TabsList>

          {/* AVAILABLE */}
          <TabsContent value="available" className="mt-4">
            {/* Filter row */}
            <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
              <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
              {['all', 'photo', 'voice', 'video'].map(t => (
                <Button
                  key={t}
                  variant={filterType === t ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterType(t)}
                  className={`rounded-sm capitalize ${filterType === t ? 'bg-amber-500 text-black' : 'border-border/40'}`}
                  data-testid={`field-ops-filter-${t}`}
                >
                  {t}
                </Button>
              ))}
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : filteredOps.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground text-sm">No ops match the filter.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="field-ops-list">
                {filteredOps.map(op => {
                  const Icon = ICON_BY_TYPE[op.type] || Camera;
                  return (
                    <Card
                      key={op.op_id}
                      className={`bg-surface/50 ${BORDER_BY_TYPE[op.type] || 'border-border/30'} rounded-sm hover:bg-surface/70 transition cursor-pointer`}
                      onClick={() => acceptOp(op)}
                      data-testid={`field-op-${op.op_id}`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-sm bg-black/30 ${COLOR_BY_TYPE[op.type]}`}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2 mb-1">
                              <h3 className="font-cinzel text-sm leading-tight truncate">{op.title}</h3>
                              <Badge variant="outline" className={`shrink-0 ${COLOR_BY_TYPE[op.type]} border-current/30 text-[10px] uppercase tracking-wider`}>
                                {op.type}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{op.summary}</p>
                            <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                              <div className="flex items-center gap-3">
                                <span className="font-mono text-emerald-400" data-testid={`field-op-${op.op_id}-pay`}>
                                  VE${op.upfront_ve.toFixed(2)}
                                </span>
                                {op.geo_bonus_ve > 0 && (
                                  <span className="font-mono text-amber-400">+VE${op.geo_bonus_ve.toFixed(2)} geo</span>
                                )}
                                {op.distance_m !== null && (
                                  <span className="flex items-center gap-1 text-muted-foreground">
                                    <MapPin className="w-3 h-3" />{(op.distance_m / 1000).toFixed(2)}km
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="flex items-center gap-1 text-muted-foreground">
                                  <Clock className="w-3 h-3" />~{op.duration_minutes_estimate}m
                                </span>
                                {op.review_mode === 'human' && (
                                  <Badge variant="outline" className="border-fuchsia-400/40 text-fuchsia-300 text-[10px]">
                                    Reviewed
                                  </Badge>
                                )}
                                {op.accepted_by_me && (
                                  <Badge className="bg-amber-500 text-black text-[10px]">In Progress</Badge>
                                )}
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="w-5 h-5 text-muted-foreground/40 shrink-0 self-center" />
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* HISTORY */}
          <TabsContent value="history" className="mt-4">
            {history.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground text-sm">No submissions yet — accept an op to get started.</div>
            ) : (
              <div className="space-y-2" data-testid="field-ops-history">
                {history.map(sub => <SubmissionRow key={sub.submission_id} sub={sub} />)}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Capture dialog */}
      <Dialog open={!!activeOp} onOpenChange={(open) => { if (!open) { setActiveOp(null); setCaptureBlob(null); setPreviewUrl(null); } }}>
        <DialogContent className="bg-obsidian border-border/40 max-w-2xl max-h-[92vh] overflow-y-auto" data-testid="field-ops-capture-dialog">
          {activeOp && (
            <CaptureFlow
              op={activeOp}
              captureBlob={captureBlob}
              setCaptureBlob={setCaptureBlob}
              setCaptureMime={setCaptureMime}
              setCaptureDurationMs={setCaptureDurationMs}
              previewUrl={previewUrl}
              setPreviewUrl={setPreviewUrl}
              notes={notes}
              setNotes={setNotes}
              submitting={submitting}
              onSubmit={submitOp}
              onCancel={() => { setActiveOp(null); setCaptureBlob(null); setPreviewUrl(null); }}
              geo={geo}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Result dialog */}
      <Dialog open={!!resultModal} onOpenChange={(open) => { if (!open) setResultModal(null); }}>
        <DialogContent className="bg-obsidian border-border/40 max-w-md" data-testid="field-ops-result-dialog">
          {resultModal && (
            <>
              <DialogHeader>
                <DialogTitle className="font-cinzel flex items-center gap-2">
                  {resultModal.status === 'auto_approved' || resultModal.status === 'approved' ? (
                    <><CheckCircle2 className="w-5 h-5 text-emerald-400" /> Approved!</>
                  ) : resultModal.status === 'queued_review' ? (
                    <><Clock className="w-5 h-5 text-amber-400" /> Queued for Review</>
                  ) : (
                    <><XCircle className="w-5 h-5 text-rose-400" /> Rejected</>
                  )}
                </DialogTitle>
                <DialogDescription className="text-muted-foreground">{resultModal.opTitle}</DialogDescription>
              </DialogHeader>
              <div className="space-y-3 mt-2">
                {resultModal.quality_check && (
                  <div className="text-xs space-y-1">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Quality score</span>
                      <span className="font-mono">{Math.round((resultModal.quality_check.score || 0) * 100)}%</span>
                    </div>
                    <p className="text-muted-foreground italic">{resultModal.quality_check.reason}</p>
                  </div>
                )}
                {resultModal.paid_ve > 0 && (
                  <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-sm p-3 flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Paid out</span>
                    <span className="font-mono text-emerald-400 text-lg" data-testid="field-ops-paid">
                      +VE${resultModal.paid_ve.toFixed(2)}
                    </span>
                  </div>
                )}
                {resultModal.boost_applied && (
                  <Badge className="bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/40">
                    <Sparkles className="w-3 h-3 mr-1" /> Forge Surge boost active
                  </Badge>
                )}
                {resultModal.geo_valid && (
                  <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/40 ml-2">
                    <MapPin className="w-3 h-3 mr-1" /> Geo bonus +20%
                  </Badge>
                )}
                {resultModal.status === 'queued_review' && (
                  <p className="text-xs text-muted-foreground">
                    A reviewer will assess your submission. You&apos;ll see VE$ in your wallet on approval.
                  </p>
                )}
                <Button
                  onClick={() => setResultModal(null)}
                  className="w-full bg-amber-500 hover:bg-amber-600 text-black rounded-sm"
                  data-testid="field-ops-result-close"
                >
                  Continue
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// =========== Capture Flow Component (handles all 3 types) ===========

const CaptureFlow = ({ op, captureBlob, setCaptureBlob, setCaptureMime, setCaptureDurationMs,
                       previewUrl, setPreviewUrl, notes, setNotes, submitting, onSubmit, onCancel, geo: _geo }) => {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const startTimeRef = useRef(null);
  const [phase, setPhase] = useState('idle');   // idle | live | recording | review
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      stopStream();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
  };

  const startCamera = (typ) => {
    (async () => {
      try {
        const constraints = typ === 'voice'
          ? { audio: true }
          : typ === 'video'
            ? { audio: true, video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } }
            : { video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        streamRef.current = stream;
        if (videoRef.current && typ !== 'voice') {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        setPhase('live');
      } catch (e) {
        toast.error(`Camera/mic access denied: ${e.message}`);
      }
    })();
  };

  const snapPhoto = () => {
    const v = videoRef.current;
    if (!v) return;
    const canvas = document.createElement('canvas');
    canvas.width = v.videoWidth || 1280;
    canvas.height = v.videoHeight || 720;
    canvas.getContext('2d').drawImage(v, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      setCaptureBlob(blob);
      setCaptureMime('image/jpeg');
      setCaptureDurationMs(null);
      setPreviewUrl(URL.createObjectURL(blob));
      stopStream();
      setPhase('review');
    }, 'image/jpeg', 0.85);
  };

  const startRecording = (typ) => {
    if (!streamRef.current) return;
    const candidates = typ === 'voice'
      ? ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
      : ['video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4'];
    const mimeType = candidates.find(m => window.MediaRecorder && MediaRecorder.isTypeSupported(m)) || '';
    try {
      const rec = mimeType ? new MediaRecorder(streamRef.current, { mimeType }) : new MediaRecorder(streamRef.current);
      chunksRef.current = [];
      rec.ondataavailable = (ev) => { if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data); };
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: rec.mimeType });
        const baseMime = (rec.mimeType || '').split(';')[0];
        const dur = startTimeRef.current ? Date.now() - startTimeRef.current : null;
        setCaptureBlob(blob);
        setCaptureMime(baseMime || (typ === 'voice' ? 'audio/webm' : 'video/webm'));
        setCaptureDurationMs(dur);
        setPreviewUrl(URL.createObjectURL(blob));
        stopStream();
        setPhase('review');
        if (timerRef.current) clearInterval(timerRef.current);
      };
      recorderRef.current = rec;
      rec.start();
      startTimeRef.current = Date.now();
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000)), 250);
      setPhase('recording');
    } catch (e) {
      toast.error(`Recording start failed: ${e.message}`);
    }
  };

  const stopRecording = () => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
  };

  const retake = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setCaptureBlob(null);
    setCaptureMime(null);
    setCaptureDurationMs(null);
    setPhase('idle');
  };

  const IconForType = ICON_BY_TYPE[op.type] || Camera;

  return (
    <>
      <DialogHeader>
        <DialogTitle className="font-cinzel flex items-center gap-2">
          <IconForType className={`w-5 h-5 ${COLOR_BY_TYPE[op.type]}`} />
          {op.title}
        </DialogTitle>
        <DialogDescription className="text-muted-foreground">{op.summary}</DialogDescription>
      </DialogHeader>

      {/* Instructions */}
      <div className="bg-surface/40 border border-border/30 rounded-sm p-3 text-xs">
        <p className="text-muted-foreground mb-1.5 font-cinzel uppercase text-[10px] tracking-wider">Instructions</p>
        <ul className="space-y-1">
          {(op.instructions || []).map((line, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-amber-400 mt-0.5">•</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
        {op.prompt_text && (
          <div className="mt-3 p-2 bg-black/30 border border-amber-500/30 rounded-sm">
            <p className="text-[10px] text-amber-400 uppercase tracking-wider mb-1">Read this aloud</p>
            <p className="font-cinzel text-sm">{op.prompt_text}</p>
          </div>
        )}
      </div>

      {/* Reward summary */}
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          <DollarSign className="w-3 h-3 mr-1" /> VE${op.base_reward_ve.toFixed(2)} upfront
        </Badge>
        {op.geo_required && (
          <Badge className="bg-amber-500/20 text-amber-300 border border-amber-500/40">
            <MapPin className="w-3 h-3 mr-1" /> +20% if on-site
          </Badge>
        )}
        {op.base_reward_ve >= 5 && (
          <Badge className="bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/40">
            <AlertTriangle className="w-3 h-3 mr-1" /> Human reviewed
          </Badge>
        )}
      </div>

      {/* Capture area */}
      <div className="bg-black border border-border/40 rounded-sm overflow-hidden aspect-video flex items-center justify-center">
        {phase === 'idle' && !previewUrl && (
          <Button
            onClick={() => startCamera(op.type)}
            className="bg-amber-500 hover:bg-amber-600 text-black rounded-sm"
            data-testid="field-ops-start-capture"
          >
            <IconForType className="w-4 h-4 mr-2" />
            {op.type === 'voice' ? 'Enable Microphone' : op.type === 'video' ? 'Open Camera' : 'Open Camera'}
          </Button>
        )}

        {(phase === 'live' || phase === 'recording') && op.type !== 'voice' && (
          <video ref={videoRef} muted playsInline className="w-full h-full object-contain bg-black" data-testid="field-ops-video-feed" />
        )}
        {(phase === 'live' || phase === 'recording') && op.type === 'voice' && (
          <div className="text-center">
            <Mic className={`w-16 h-16 ${phase === 'recording' ? 'text-rose-400 animate-pulse' : 'text-emerald-400'} mx-auto`} />
            <p className="mt-3 font-mono text-sm">{phase === 'recording' ? `Recording... ${elapsed}s` : 'Mic armed'}</p>
          </div>
        )}

        {phase === 'review' && previewUrl && (
          <>
            {op.type === 'photo' && (
              <img src={previewUrl} alt="preview" className="w-full h-full object-contain" data-testid="field-ops-preview-img" />
            )}
            {op.type === 'voice' && (
              <div className="text-center p-4">
                <Mic className="w-12 h-12 text-emerald-400 mx-auto mb-2" />
                <audio src={previewUrl} controls className="mx-auto" data-testid="field-ops-preview-audio" />
              </div>
            )}
            {op.type === 'video' && (
              <video src={previewUrl} controls className="w-full h-full object-contain" data-testid="field-ops-preview-video" />
            )}
          </>
        )}
      </div>

      {/* Capture controls */}
      {phase === 'live' && op.type === 'photo' && (
        <Button onClick={snapPhoto} className="bg-amber-500 hover:bg-amber-600 text-black rounded-sm" data-testid="field-ops-snap">
          <Camera className="w-4 h-4 mr-2" /> Capture Photo
        </Button>
      )}
      {phase === 'live' && (op.type === 'voice' || op.type === 'video') && (
        <Button onClick={() => startRecording(op.type)} className="bg-rose-500 hover:bg-rose-600 text-white rounded-sm" data-testid="field-ops-rec-start">
          <Play className="w-4 h-4 mr-2" /> Start Recording
        </Button>
      )}
      {phase === 'recording' && (
        <Button onClick={stopRecording} className="bg-emerald-500 hover:bg-emerald-600 text-black rounded-sm" data-testid="field-ops-rec-stop">
          <Square className="w-4 h-4 mr-2" /> Stop ({elapsed}s)
        </Button>
      )}
      {phase === 'review' && (
        <div className="space-y-3">
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional notes (location, environment, language, etc.)"
            className="bg-surface/40 border-border/40 rounded-sm text-sm resize-none"
            rows={2}
            data-testid="field-ops-notes"
          />
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" onClick={retake} className="rounded-sm border-border/40" data-testid="field-ops-retake">
              <RotateCcw className="w-4 h-4 mr-2" /> Retake
            </Button>
            <Button
              onClick={onSubmit}
              disabled={submitting || !captureBlob}
              className="bg-amber-500 hover:bg-amber-600 text-black rounded-sm"
              data-testid="field-ops-submit"
            >
              {submitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Submit{_geo && op.geo_required ? ' (with geo)' : ''}
            </Button>
          </div>
        </div>
      )}

      <Button variant="ghost" onClick={onCancel} className="text-muted-foreground text-xs" data-testid="field-ops-cancel">
        Cancel & release lock
      </Button>
    </>
  );
};

export default FieldOps;
