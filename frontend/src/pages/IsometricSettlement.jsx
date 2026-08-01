import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, Hammer, RotateCcw, Save, Users, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import JarvisPanel from '@/components/JarvisPanel';
import DesktopDiagnostics from '@/components/DesktopDiagnostics';
import CausalLedgerPanel from '@/components/CausalLedgerPanel';
import { appendCausalEvent } from '@/lib/causalLedger';
import { readDurable, writeDurable } from '@/lib/desktopStorage';
import './IsometricSettlement.css';

const MAP_SIZE = 18;
const TILE_W = 64;
const TILE_H = 32;
const STORAGE_KEY = 'eov-isometric-alpha-state';

const INITIAL_WORLD = {
  player: { x: 8, y: 9 },
  blueprints: [
    { id: 'hall', x: 8, y: 5, type: 'town_hall', stage: 4, name: 'Founders Hall' },
    { id: 'lab', x: 12, y: 8, type: 'laboratory', stage: 2, name: 'Generator Laboratory' },
    { id: 'store', x: 5, y: 11, type: 'storehouse', stage: 3, name: 'Community Storehouse' },
  ],
};

const NPCS = [
  { id: 'ada', name: 'Ada', role: 'AI Engineer', x: 10, y: 7, color: '#67e8f9' },
  { id: 'orin', name: 'Orin', role: 'Builder', x: 6, y: 9, color: '#fbbf24' },
  { id: 'mira', name: 'Mira', role: 'Researcher', x: 11, y: 11, color: '#c084fc' },
];

const BUILDINGS = {
  town_hall: { label: 'Founders Hall', color: '#c79a3b', roof: '#7c4f21', footprint: [2, 2] },
  laboratory: { label: 'Generator Lab', color: '#4d8b99', roof: '#274c5a', footprint: [2, 2] },
  storehouse: { label: 'Storehouse', color: '#8b6c4a', roof: '#553d29', footprint: [2, 1] },
  workshop: { label: 'Workshop', color: '#a86235', roof: '#63371f', footprint: [2, 2] },
};

const clamp = (value) => Math.max(0, Math.min(MAP_SIZE - 1, value));

function worldToScreen(x, y, originX, originY) {
  return {
    x: originX + (x - y) * (TILE_W / 2),
    y: originY + (x + y) * (TILE_H / 2),
  };
}

function drawDiamond(ctx, cx, cy, fill, stroke = 'rgba(0,0,0,.18)') {
  ctx.beginPath();
  ctx.moveTo(cx, cy - TILE_H / 2);
  ctx.lineTo(cx + TILE_W / 2, cy);
  ctx.lineTo(cx, cy + TILE_H / 2);
  ctx.lineTo(cx - TILE_W / 2, cy);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.stroke();
}

function drawPrism(ctx, cx, cy, width, depth, height, color, roof, alpha = 1) {
  const hw = (TILE_W * width) / 2;
  const hd = (TILE_H * depth) / 2;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(cx - hw, cy - height);
  ctx.lineTo(cx, cy - height + hd);
  ctx.lineTo(cx, cy + hd);
  ctx.lineTo(cx - hw, cy);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = `${color}cc`;
  ctx.beginPath();
  ctx.moveTo(cx, cy - height + hd);
  ctx.lineTo(cx + hw, cy - height);
  ctx.lineTo(cx + hw, cy);
  ctx.lineTo(cx, cy + hd);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = roof;
  ctx.beginPath();
  ctx.moveTo(cx, cy - height - hd);
  ctx.lineTo(cx + hw, cy - height);
  ctx.lineTo(cx, cy - height + hd);
  ctx.lineTo(cx - hw, cy - height);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

const IsometricSettlement = () => {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const frameRef = useRef(null);
  const [world, setWorld] = useState(INITIAL_WORLD);
  const [buildMode, setBuildMode] = useState(false);
  const [selectedType, setSelectedType] = useState('workshop');
  const [hoverTile, setHoverTile] = useState(null);
  const [selected, setSelected] = useState(null);
  const [savedAt, setSavedAt] = useState(null);

  const settlementStats = useMemo(() => ({
    residents: NPCS.length + 1,
    structures: world.blueprints.length,
    activeProjects: world.blueprints.filter((item) => item.stage < 4).length,
  }), [world.blueprints]);

  useEffect(() => {
    localStorage.setItem('eovLastRoute', '/play');
    let active = true;
    readDurable('world', STORAGE_KEY, INITIAL_WORLD).then((saved) => {
      if (active && saved?.player && Array.isArray(saved.blueprints)) setWorld(saved);
    });
    return () => { active = false; };
  }, []);

  const saveWorld = useCallback(async (nextWorld = world) => {
    const envelope = await writeDurable('world', STORAGE_KEY, nextWorld);
    setSavedAt(new Date(envelope.savedAt));
  }, [world]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(800, rect.width);
    const height = Math.max(600, rect.height);
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, '#07131b');
    gradient.addColorStop(1, '#020608');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    const originX = width / 2;
    const originY = 72;
    for (let sum = 0; sum <= (MAP_SIZE - 1) * 2; sum += 1) {
      for (let x = 0; x < MAP_SIZE; x += 1) {
        const y = sum - x;
        if (y < 0 || y >= MAP_SIZE) continue;
        const point = worldToScreen(x, y, originX, originY);
        const road = x === 8 || y === 9;
        const checker = (x + y) % 2 === 0;
        drawDiamond(ctx, point.x, point.y, road ? '#49545a' : checker ? '#304d3a' : '#294433');
        if (hoverTile?.x === x && hoverTile?.y === y) {
          drawDiamond(ctx, point.x, point.y, buildMode ? 'rgba(212,175,55,.42)' : 'rgba(103,232,249,.25)', '#d4af37');
        }

        const structure = world.blueprints.find((item) => item.x === x && item.y === y);
        if (structure) {
          const spec = BUILDINGS[structure.type];
          const completion = structure.stage / 4;
          if (structure.stage === 1) {
            ctx.strokeStyle = '#d4af37';
            ctx.setLineDash([5, 4]);
            ctx.strokeRect(point.x - 28, point.y - 12, 56, 24);
            ctx.setLineDash([]);
          } else {
            drawPrism(ctx, point.x, point.y, spec.footprint[0], spec.footprint[1], 24 + completion * 48, spec.color, spec.roof, 0.62 + completion * 0.095);
          }
        }

        const npc = NPCS.find((item) => item.x === x && item.y === y);
        if (npc) {
          ctx.fillStyle = npc.color;
          ctx.beginPath();
          ctx.arc(point.x, point.y - 24, 8, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#0b1014';
          ctx.fillRect(point.x - 6, point.y - 16, 12, 19);
        }

        if (world.player.x === x && world.player.y === y) {
          ctx.fillStyle = '#f6d365';
          ctx.beginPath();
          ctx.arc(point.x, point.y - 27, 9, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#4f46e5';
          ctx.fillRect(point.x - 7, point.y - 18, 14, 22);
          ctx.strokeStyle = '#f6d365';
          ctx.strokeRect(point.x - 10, point.y - 31, 20, 36);
        }
      }
    }

    ctx.fillStyle = 'rgba(3,8,11,.76)';
    ctx.fillRect(18, height - 50, 470, 32);
    ctx.fillStyle = '#d9c991';
    ctx.font = '13px JetBrains Mono, monospace';
    ctx.fillText(buildMode ? 'BUILD MODE Â· Select a tile to place a staged blueprint' : 'MOVE Â· WASD / arrow keys Â· Click a structure or resident to inspect', 32, height - 29);
  }, [buildMode, hoverTile, world]);

  useEffect(() => {
    const tick = () => {
      render();
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [render]);

  useEffect(() => {
    const onKeyDown = (event) => {
      const key = event.key.toLowerCase();
      const delta = {
        w: [0, -1], arrowup: [0, -1],
        s: [0, 1], arrowdown: [0, 1],
        a: [-1, 0], arrowleft: [-1, 0],
        d: [1, 0], arrowright: [1, 0],
      }[key];
      if (!delta || buildMode) return;
      event.preventDefault();
      setWorld((current) => ({
        ...current,
        player: { x: clamp(current.player.x + delta[0]), y: clamp(current.player.y + delta[1]) },
      }));
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [buildMode]);

  const eventToTile = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const sx = event.clientX - rect.left;
    const sy = event.clientY - rect.top;
    const originX = rect.width / 2;
    const originY = 72;
    const tx = (sx - originX) / (TILE_W / 2);
    const ty = (sy - originY) / (TILE_H / 2);
    return { x: Math.round((tx + ty) / 2), y: Math.round((ty - tx) / 2) };
  };

  const handlePointerMove = (event) => {
    const tile = eventToTile(event);
    setHoverTile(tile.x >= 0 && tile.y >= 0 && tile.x < MAP_SIZE && tile.y < MAP_SIZE ? tile : null);
  };

  const handleCanvasClick = () => {
    if (!hoverTile) return;
    const structure = world.blueprints.find((item) => item.x === hoverTile.x && item.y === hoverTile.y);
    const npc = NPCS.find((item) => item.x === hoverTile.x && item.y === hoverTile.y);
    if (buildMode) {
      if (structure || npc || (world.player.x === hoverTile.x && world.player.y === hoverTile.y)) return;
      const nextWorld = {
        ...world,
        blueprints: [...world.blueprints, {
          id: crypto.randomUUID(), x: hoverTile.x, y: hoverTile.y,
          type: selectedType, stage: 1, name: BUILDINGS[selectedType].label,
        }],
      };
      setWorld(nextWorld);
      saveWorld(nextWorld);
      appendCausalEvent({ actionId: `construct:${nextWorld.blueprints.at(-1).id}`, actorId: localStorage.getItem('currentCharacterId') || 'unknown', state: 'proposed', intent: `Construct ${BUILDINGS[selectedType].label}`, location: `${hoverTile.x},${hoverTile.y}`, parentEventIds: [], inputs: { blueprintType: selectedType }, outputs: {}, evidence: [], physicalEffect: false });
      setBuildMode(false);
      return;
    }
    setSelected(structure || npc || null);
  };

  const advanceConstruction = () => {
    if (!selected?.stage || selected.stage >= 4) return;
    const nextWorld = {
      ...world,
      blueprints: world.blueprints.map((item) => item.id === selected.id ? { ...item, stage: item.stage + 1 } : item),
    };
    setWorld(nextWorld);
    setSelected({ ...selected, stage: selected.stage + 1 });
    saveWorld(nextWorld);
    appendCausalEvent({ actionId: `construct:${selected.id}`, actorId: localStorage.getItem('currentCharacterId') || 'unknown', state: selected.stage === 1 ? 'accepted' : selected.stage === 2 ? 'reserved' : 'in_progress', intent: `Advance ${selected.name} to stage ${selected.stage + 1}`, location: `${selected.x},${selected.y}`, parentEventIds: [], inputs: { priorStage: selected.stage }, outputs: { stage: selected.stage + 1 }, evidence: [{ kind: 'player_confirmation' }], physicalEffect: selected.stage >= 3 });
  };

  const resetSettlement = () => {
    setWorld(INITIAL_WORLD);
    setSelected(null);
    saveWorld(INITIAL_WORLD);
  };

  return (
    <div className="iso-shell">
      <header className="iso-header">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/select-mode')} aria-label="Back to modes"><ArrowLeft /></Button>
          <div>
            <p className="iso-kicker">ECHOES OF VIRTUALITY Â· ALPHA 0.2</p>
            <h1>Founders' Settlement</h1>
          </div>
        </div>
        <div className="iso-stats">
          <span><Users size={15} /> {settlementStats.residents} residents</span>
          <span><Building2 size={15} /> {settlementStats.structures} structures</span>
          <span><Hammer size={15} /> {settlementStats.activeProjects} active</span>
        </div>
      </header>

      <main className="iso-main">
        <section className="iso-viewport" aria-label="Isometric settlement viewport">
          <canvas ref={canvasRef} onMouseMove={handlePointerMove} onMouseLeave={() => setHoverTile(null)} onClick={handleCanvasClick} />
          <div className="iso-controls">
            <Button className={buildMode ? 'bg-gold text-black' : ''} variant={buildMode ? 'default' : 'outline'} onClick={() => setBuildMode((value) => !value)}>
              <Hammer size={16} /> {buildMode ? 'Cancel build' : 'Place blueprint'}
            </Button>
            {buildMode && (
              <select value={selectedType} onChange={(event) => setSelectedType(event.target.value)} aria-label="Blueprint type">
                <option value="workshop">Workshop</option>
                <option value="laboratory">Generator laboratory</option>
                <option value="storehouse">Storehouse</option>
              </select>
            )}
            <Button variant="outline" onClick={() => saveWorld()}><Save size={16} /> Save</Button>
            <Button variant="ghost" onClick={resetSettlement}><RotateCcw size={16} /> Reset</Button>
          </div>
        </section>

        <aside className="iso-sidebar">
          <div>
            <p className="iso-kicker">SETTLEMENT LEDGER</p>
            <h2>Construction activity</h2>
          </div>
          <div className="iso-projects">
            {world.blueprints.map((item) => (
              <button key={item.id} className={selected?.id === item.id ? 'selected' : ''} onClick={() => setSelected(item)}>
                <span>{item.name}</span>
                <Badge variant="outline">Stage {item.stage}/4</Badge>
                <div className="iso-progress"><i style={{ width: `${item.stage * 25}%` }} /></div>
              </button>
            ))}
          </div>

          <div className="iso-inspector">
            <p className="iso-kicker">INSPECTOR</p>
            {selected ? (
              <>
                <h3>{selected.name}</h3>
                <p>{selected.role || (selected.stage === 4 ? 'Commissioned structure' : 'Construction work order pending verification')}</p>
                {selected.stage && selected.stage < 4 && (
                  <Button onClick={advanceConstruction}><Zap size={16} /> Complete verified stage</Button>
                )}
              </>
            ) : <p>Select a resident or structure in the settlement.</p>}
          </div>

          <div className="iso-note">
            <strong>Desktop persistence</strong>
            <p>The desktop build stores checksummed revisions with a known-good backup. Server-authoritative work orders and CU escrow remain a later milestone.</p>
            {savedAt && <small>Saved {savedAt.toLocaleTimeString()}</small>}
          </div>
          <JarvisPanel activity={buildMode ? 'Observing blueprint placement' : selected ? `Reviewing ${selected.name}` : 'Monitoring settlement activity'} />
          <DesktopDiagnostics />
          <CausalLedgerPanel />
        </aside>
      </main>
    </div>
  );
};

export default IsometricSettlement;
