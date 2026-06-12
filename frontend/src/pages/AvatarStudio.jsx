import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, Pencil, Eraser, PaintBucket, Pipette, Undo2, Trash2,
  Save, RefreshCw, Lock, Sparkles, ShoppingBag, Star
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import PixelAvatar from '@/components/PixelAvatar';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const GRID = 64;
const SCALE = 8;

const AvatarStudio = () => {
  const navigate = useNavigate();
  const userId = localStorage.getItem('userId');
  const canvasRef = useRef(null);
  const previewRef = useRef(null);
  const pixelsRef = useRef(new Array(GRID * GRID).fill(null)); // hex or null
  const undoRef = useRef([]);
  const drawingRef = useRef(false);

  const [tool, setTool] = useState('pencil');
  const [color, setColor] = useState('#FFD700');
  const [brush, setBrush] = useState(1);
  const [palettes, setPalettes] = useState(null);
  const [frame, setFrame] = useState(null);
  const [hasAvatar, setHasAvatar] = useState(false);
  const [saving, setSaving] = useState(false);
  const [spotlight, setSpotlight] = useState([]);
  const [balance, setBalance] = useState(0);
  const [previewUrl, setPreviewUrl] = useState(null);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const px = pixelsRef.current;
    // checkerboard transparency background
    for (let y = 0; y < GRID; y++) {
      for (let x = 0; x < GRID; x++) {
        ctx.fillStyle = (x + y) % 2 === 0 ? '#1c1c20' : '#222228';
        ctx.fillRect(x * SCALE, y * SCALE, SCALE, SCALE);
        const c = px[y * GRID + x];
        if (c) {
          ctx.fillStyle = c;
          ctx.fillRect(x * SCALE, y * SCALE, SCALE, SCALE);
        }
      }
    }
    // mini preview
    const pv = previewRef.current;
    if (pv) {
      const pctx = pv.getContext('2d');
      pctx.clearRect(0, 0, GRID, GRID);
      for (let i = 0; i < px.length; i++) {
        if (px[i]) {
          pctx.fillStyle = px[i];
          pctx.fillRect(i % GRID, Math.floor(i / GRID), 1, 1);
        }
      }
    }
  }, []);

  useEffect(() => {
    if (!userId) { navigate('/auth'); return; }
    (async () => {
      try {
        const [palRes, avRes, spotRes, walRes] = await Promise.all([
          axios.get(`${API}/avatar/palettes?user_id=${userId}`),
          axios.get(`${API}/avatar/user/${userId}`),
          axios.get(`${API}/cosmetics/spotlight`),
          axios.get(`${API}/cosmetics/wallet/${userId}`)
        ]);
        setPalettes(palRes.data);
        setSpotlight(spotRes.data.featured || []);
        setBalance(walRes.data.balance_ve || 0);
        const av = avRes.data;
        setFrame(av.frame);
        setHasAvatar(av.has_avatar);
        if (av.has_avatar && av.pixels && av.palette) {
          pixelsRef.current = av.pixels.map(i => (i >= 0 ? av.palette[i] : null));
          setPreviewUrl(av.data_url);
        }
      } catch (e) {
        toast.error('Failed to load Avatar Studio');
      }
      redraw();
    })();
  }, [userId, navigate, redraw]);

  const pushUndo = () => {
    undoRef.current.push([...pixelsRef.current]);
    if (undoRef.current.length > 30) undoRef.current.shift();
  };

  const getCell = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor(((e.clientX - rect.left) / rect.width) * GRID);
    const y = Math.floor(((e.clientY - rect.top) / rect.height) * GRID);
    if (x < 0 || x >= GRID || y < 0 || y >= GRID) return null;
    return { x, y };
  };

  const paintCell = (x, y) => {
    const px = pixelsRef.current;
    const half = Math.floor(brush / 2);
    for (let dy = -half; dy < brush - half; dy++) {
      for (let dx = -half; dx < brush - half; dx++) {
        const nx = x + dx, ny = y + dy;
        if (nx >= 0 && nx < GRID && ny >= 0 && ny < GRID) {
          px[ny * GRID + nx] = tool === 'eraser' ? null : color;
        }
      }
    }
  };

  const floodFill = (x, y) => {
    const px = pixelsRef.current;
    const target = px[y * GRID + x];
    if (target === color) return;
    const stack = [[x, y]];
    while (stack.length) {
      const [cx, cy] = stack.pop();
      if (cx < 0 || cx >= GRID || cy < 0 || cy >= GRID) continue;
      if (px[cy * GRID + cx] !== target) continue;
      px[cy * GRID + cx] = color;
      stack.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
    }
  };

  const handlePointerDown = (e) => {
    e.preventDefault();
    const cell = getCell(e);
    if (!cell) return;
    if (tool === 'eyedropper') {
      const c = pixelsRef.current[cell.y * GRID + cell.x];
      if (c) { setColor(c); setTool('pencil'); }
      return;
    }
    pushUndo();
    drawingRef.current = true;
    if (tool === 'fill') {
      floodFill(cell.x, cell.y);
      drawingRef.current = false;
    } else {
      paintCell(cell.x, cell.y);
    }
    redraw();
  };

  const handlePointerMove = (e) => {
    if (!drawingRef.current) return;
    const cell = getCell(e);
    if (!cell) return;
    paintCell(cell.x, cell.y);
    redraw();
  };

  const handlePointerUp = () => { drawingRef.current = false; };

  const undo = () => {
    const prev = undoRef.current.pop();
    if (prev) { pixelsRef.current = prev; redraw(); }
  };

  const clearAll = () => {
    pushUndo();
    pixelsRef.current = new Array(GRID * GRID).fill(null);
    redraw();
  };

  const saveAvatar = async () => {
    const px = pixelsRef.current;
    if (!px.some(c => c)) { toast.error('Draw something first!'); return; }
    setSaving(true);
    try {
      // build palette + indices
      const palette = [];
      const map = {};
      const indices = px.map(c => {
        if (!c) return -1;
        if (map[c] === undefined) {
          if (palette.length >= 64) return 0; // safety cap
          map[c] = palette.length;
          palette.push(c);
        }
        return map[c];
      });
      // render 64x64 PNG
      const off = document.createElement('canvas');
      off.width = GRID; off.height = GRID;
      const ctx = off.getContext('2d');
      for (let i = 0; i < px.length; i++) {
        if (px[i]) {
          ctx.fillStyle = px[i];
          ctx.fillRect(i % GRID, Math.floor(i / GRID), 1, 1);
        }
      }
      const dataUrl = off.toDataURL('image/png');
      await axios.put(`${API}/avatar/user/${userId}`, { pixels: indices, palette, data_url: dataUrl });
      setPreviewUrl(dataUrl);
      setHasAvatar(true);
      toast.success('Avatar saved! It now represents you across the Echoes.');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save avatar');
    }
    setSaving(false);
  };

  const buySpotlight = async () => {
    if (!hasAvatar) { toast.error('Save an avatar first'); return; }
    try {
      const res = await axios.post(`${API}/cosmetics/purchase`, { user_id: userId, item_id: 'spotlight_24h' });
      setBalance(res.data.new_balance);
      toast.success('You are featured in the Hall of Echoes for 24h!');
      const spotRes = await axios.get(`${API}/cosmetics/spotlight`);
      setSpotlight(spotRes.data.featured || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Spotlight purchase failed');
    }
  };

  const ToolBtn = ({ id, icon: Icon, label }) => (
    <Button
      variant={tool === id ? 'default' : 'outline'}
      size="sm"
      onClick={() => setTool(id)}
      className={tool === id ? 'bg-gold text-black hover:bg-gold' : 'border-border/40'}
      data-testid={`tool-${id}`}
      title={label}
    >
      <Icon className="w-4 h-4" />
    </Button>
  );

  const ColorSwatch = ({ hex, locked }) => (
    <button
      onClick={() => {
        if (locked) { toast.info('Unlock this palette pack in the VE$ Boutique'); return; }
        setColor(hex);
        if (tool === 'eraser') setTool('pencil');
      }}
      className={`relative w-7 h-7 rounded-sm border transition-transform hover:scale-110 ${color === hex && !locked ? 'border-white ring-1 ring-white' : 'border-black/40'} ${locked ? 'opacity-40 cursor-not-allowed' : ''}`}
      style={{ backgroundColor: hex }}
      data-testid={`swatch-${hex.replace('#', '')}`}
    >
      {locked && <Lock className="absolute inset-0 m-auto w-3 h-3 text-white drop-shadow" />}
    </button>
  );

  return (
    <div className="min-h-screen bg-obsidian text-foreground">
      <div className="bg-surface/50 border-b border-border/30 p-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="studio-back-btn">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-cinzel text-2xl text-gold flex items-center gap-2">
                <Sparkles className="w-6 h-6" /> Avatar Studio
              </h1>
              <p className="text-sm text-muted-foreground">Design your 64×64 pixel logo — your identity in the Echoes</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className="bg-green-500/10 text-green-400 border-green-500/30" data-testid="studio-ve-balance">
              {balance.toFixed(2)} VE$
            </Badge>
            <Button variant="outline" onClick={() => navigate('/boutique')} className="border-gold/30 text-gold hover:bg-gold/10" data-testid="open-boutique-btn">
              <ShoppingBag className="w-4 h-4 mr-2" /> Boutique
            </Button>
            <Button onClick={saveAvatar} disabled={saving} className="bg-gold text-black hover:bg-gold-light" data-testid="save-avatar-btn">
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Save Avatar
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4 grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        {/* Editor */}
        <Card className="p-4 bg-surface/50 border-border/30">
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <ToolBtn id="pencil" icon={Pencil} label="Pencil" />
            <ToolBtn id="eraser" icon={Eraser} label="Eraser" />
            <ToolBtn id="fill" icon={PaintBucket} label="Fill" />
            <ToolBtn id="eyedropper" icon={Pipette} label="Pick color" />
            <div className="w-px h-6 bg-border/40 mx-1" />
            {[1, 2, 4].map(b => (
              <Button key={b} variant={brush === b ? 'default' : 'outline'} size="sm"
                onClick={() => setBrush(b)}
                className={brush === b ? 'bg-slate-blue text-white' : 'border-border/40'}
                data-testid={`brush-${b}`}>
                {b}px
              </Button>
            ))}
            <div className="w-px h-6 bg-border/40 mx-1" />
            <Button variant="outline" size="sm" onClick={undo} className="border-border/40" data-testid="undo-btn">
              <Undo2 className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={clearAll} className="border-red-500/30 text-red-400" data-testid="clear-btn">
              <Trash2 className="w-4 h-4" />
            </Button>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Current</span>
              <div className="w-7 h-7 rounded-sm border border-white/30" style={{ backgroundColor: color }} data-testid="current-color" />
            </div>
          </div>

          <canvas
            ref={canvasRef}
            width={GRID * SCALE}
            height={GRID * SCALE}
            className="w-full max-w-[512px] mx-auto block border border-border/40 rounded-sm touch-none cursor-crosshair"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            data-testid="pixel-canvas"
          />

          {/* Palette */}
          <div className="mt-4 space-y-3">
            <div>
              <p className="text-xs text-muted-foreground mb-1.5 uppercase tracking-wider">Base Palette</p>
              <div className="flex flex-wrap gap-1.5">
                {(palettes?.base_palette || []).map(hex => <ColorSwatch key={hex} hex={hex} locked={false} />)}
              </div>
            </div>
            {(palettes?.packs || []).map(pack => (
              <div key={pack.pack_id}>
                <p className="text-xs text-muted-foreground mb-1.5 uppercase tracking-wider flex items-center gap-2">
                  {pack.name}
                  {!pack.owned && <Badge variant="outline" className="text-[10px] border-gold/30 text-gold py-0">VE$ Boutique</Badge>}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {pack.colors.map(hex => <ColorSwatch key={`${pack.pack_id}-${hex}`} hex={hex} locked={!pack.owned} />)}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Right column */}
        <div className="space-y-4">
          <Card className="p-4 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-gold mb-3">Live Preview</h3>
            <div className="flex items-center gap-4">
              <canvas ref={previewRef} width={GRID} height={GRID}
                className={`w-24 h-24 rounded-md bg-obsidian/60 border border-border/30 ${frame ? '' : ''}`}
                style={{ imageRendering: 'pixelated' }}
                data-testid="avatar-preview" />
              <div className="space-y-1">
                <canvas width={GRID} height={GRID} ref={el => {
                  if (el && previewRef.current) {
                    const ctx = el.getContext('2d');
                    ctx.clearRect(0, 0, GRID, GRID);
                    ctx.drawImage(previewRef.current, 0, 0);
                  }
                }} className="w-8 h-8 rounded-sm bg-obsidian/60" style={{ imageRendering: 'pixelated' }} />
                <p className="text-[10px] text-muted-foreground">chat size</p>
              </div>
            </div>
            {frame && <p className="text-xs text-muted-foreground mt-2">Equipped frame: <span className="text-gold">{frame.replace('frame_', '')}</span></p>}
            {previewUrl && (
              <div className="mt-3 flex items-center gap-3">
                <PixelAvatar dataUrl={previewUrl} frame={frame} size={48} testId="saved-avatar" />
                <p className="text-xs text-muted-foreground">Last saved avatar</p>
              </div>
            )}
          </Card>

          <Card className="p-4 bg-surface/50 border-border/30">
            <h3 className="font-cinzel text-gold mb-1 flex items-center gap-2"><Star className="w-4 h-4" /> Hall of Echoes</h3>
            <p className="text-xs text-muted-foreground mb-3">Featured avatars from across the world</p>
            {spotlight.length === 0 ? (
              <p className="text-xs text-muted-foreground/60 italic">No one is featured right now. Be the first!</p>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {spotlight.map((s, i) => (
                  <div key={i} className="text-center" data-testid={`spotlight-${i}`}>
                    <PixelAvatar dataUrl={s.data_url} frame={s.frame} size={48} className="mx-auto" />
                    <p className="text-[10px] text-muted-foreground truncate mt-1">{s.display_name}</p>
                  </div>
                ))}
              </div>
            )}
            <Button onClick={buySpotlight} className="w-full mt-3 bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30" data-testid="buy-spotlight-btn">
              <Star className="w-4 h-4 mr-2" /> Feature Me — 100 VE$
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AvatarStudio;
