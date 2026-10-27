import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowLeft, Building2, CheckCircle2, Clock3, Hammer, MessageCircle, Package, Pause, Play, RotateCcw, Save, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import JarvisPanel from '@/components/JarvisPanel';
import DesktopDiagnostics from '@/components/DesktopDiagnostics';
import BuildWatermark from '@/components/BuildWatermark';
import CausalLedgerPanel from '@/components/CausalLedgerPanel';
import AuthoritativeWorkPanel from '@/components/AuthoritativeWorkPanel';
import { appendCausalEvent } from '@/lib/causalLedger';
import { readDurable, writeDurable } from '@/lib/desktopStorage';
import { fetchWorldSnapshot, submitOwnerDirective, submitWorldAction, worldServerConfigured, worldServerUrl } from '@/lib/worldServer';
import './IsometricSettlement.css';

const simulationEngine = require('@/lib/worldSimulation.cjs');
const { projectObservedFrontier } = require('@/lib/frontierView.cjs');
const { createCamera, clampZoom, tileAtPoint, visibleBounds } = require('@/lib/isometricCamera.cjs');
const { stepEntityMotion } = require('@/lib/entityMotion.cjs');
const { shouldToggleChat } = require('@/lib/gameShortcuts.cjs');
const { nearbyResidents, speechAction } = require('@/lib/worldConversation.cjs');
const { approachTileForSite, checkoutLocalStoreItem, fallbackNpcReply, formatResourceReceipt, operationForSite, resourceInteractionOptions } = require('@/lib/isometricInteractions.cjs');
const { TICK_MS, STAGES, initialSimulation, advanceSimulation, catchUpSimulation, acceptWorkOrder, playerAct, setProductionPriority } = simulationEngine;

const localPracticeEnabled = process.env.REACT_APP_ENABLE_LOCAL_PRACTICE === 'true';
const MAP_SIZE = 18;
const TILE_W = 64;
const TILE_H = 32;
const STORAGE_KEY = 'eov-isometric-alpha-state';

const INITIAL_WORLD = {
  player: { x: 8, y: 9, inventory: {}, energy: 100 },
  blueprints: [
    { id: 'hall', x: 8, y: 5, type: 'town_hall', stage: 4, name: 'Founders Hall' },
    { id: 'lab', x: 12, y: 8, type: 'laboratory', stage: 2, name: 'Generator Laboratory' },
    { id: 'store', x: 5, y: 11, type: 'storehouse', stage: 3, name: 'Community Storehouse' },
  ],
  resourceNodes: [
    { id: 'oak-1', type: 'tree', x: 2, y: 3, name: 'Old oak', stock: 10, capacity: 10 },
    { id: 'pine-1', type: 'tree', x: 3, y: 4, name: 'Pine stand', stock: 8, capacity: 8 },
    { id: 'ridge-ore-1', type: 'mineral', x: 15, y: 3, name: 'Exposed mineral seam', stock: 12, capacity: 12 },
    { id: 'well-site-1', type: 'well', x: 11, y: 13, name: 'Shallow well site', progress: 0, stock: 0, capacity: 24 },
    { id: 'field-1', type: 'farm', x: 3, y: 13, name: 'Communal farm plot', stage: 'untilled', readyTick: null, stock: 0, capacity: 12 },
    { id: 'cattle-1', type: 'cattle', x: 14, y: 13, name: 'Settlement cattle', wellbeing: 72, fedUntilTick: 0, stock: 2, capacity: 4 },
    { id: 'market-1', type: 'store', x: 7, y: 9, name: 'Dev’s tool counter', clerk: 'Dev', stock: { axe: 3, pick: 2, shovel: 2, bucket: 4, farm_tools: 2, seed: 16, feed: 12 } },
  ],
  communications: [],
};

function ensureWorldState(saved) {
  return {
    ...INITIAL_WORLD, ...saved,
    player: { ...INITIAL_WORLD.player, ...(saved?.player || {}), inventory: { ...(saved?.player?.inventory || {}) } },
    blueprints: Array.isArray(saved?.blueprints) ? saved.blueprints : INITIAL_WORLD.blueprints,
    resourceNodes: Array.isArray(saved?.resourceNodes) ? saved.resourceNodes : INITIAL_WORLD.resourceNodes,
    communications: Array.isArray(saved?.communications) ? saved.communications : [],
  };
}

function isRenderableServerSnapshot(snapshot) {
  const state = snapshot?.state;
  return Boolean(state?.clock && state?.players && state?.npcs && state?.resource_sites
    && state?.communications?.messages && state?.event?.priorities
    && state?.institutions && state?.resources && state?.survival && state?.cooking);
}

const BUILDINGS = {
  town_hall: { label: 'Founders Hall', color: '#c79a3b', roof: '#7c4f21', footprint: [2, 2] },
  laboratory: { label: 'Generator Lab', color: '#4d8b99', roof: '#274c5a', footprint: [2, 2] },
  storehouse: { label: 'Storehouse', color: '#8b6c4a', roof: '#553d29', footprint: [2, 1] },
  workshop: { label: 'Workshop', color: '#a86235', roof: '#63371f', footprint: [2, 2] },
};

const clamp = (value, maximum = MAP_SIZE - 1) => Math.max(0, Math.min(maximum, value));

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

function drawResource(ctx, point, node) {
  ctx.save();
  if (node.type === 'tree') {
    ctx.fillStyle = '#6b4423'; ctx.fillRect(point.x - 4, point.y - 31, 8, 31);
    ctx.fillStyle = node.stock ? '#2f7d45' : '#5b4b3b'; ctx.beginPath(); ctx.arc(point.x, point.y - 40, node.stock ? 18 : 8, 0, Math.PI * 2); ctx.fill();
  } else if (node.type === 'mineral') {
    ctx.fillStyle = node.stock ? '#73808a' : '#383f44';
    ctx.beginPath(); ctx.moveTo(point.x - 18, point.y); ctx.lineTo(point.x - 8, point.y - 25); ctx.lineTo(point.x + 8, point.y - 31); ctx.lineTo(point.x + 20, point.y); ctx.closePath(); ctx.fill();
  } else if (node.type === 'well') {
    ctx.strokeStyle = '#9a7b4f'; ctx.lineWidth = 5; ctx.beginPath(); ctx.ellipse(point.x, point.y - 7, 19, 10, 0, 0, Math.PI * 2); ctx.stroke();
    if (node.progress >= 3) { ctx.fillStyle = '#3d91b8'; ctx.beginPath(); ctx.ellipse(point.x, point.y - 7, 13, 6, 0, 0, Math.PI * 2); ctx.fill(); }
    if (node.installed_pump) {
      ctx.strokeStyle = node.installed_pump.status === 'failed' ? '#ef4444' : node.installed_pump.maintenance_due ? '#f59e0b' : '#8fe8ef';
      ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(point.x, point.y - 12); ctx.lineTo(point.x, point.y - 38); ctx.lineTo(point.x + 16, point.y - 43); ctx.stroke();
    }
  } else if (node.type === 'farm') {
    ctx.fillStyle = node.stage === 'ripe' ? '#b7a33d' : node.stage === 'growing' ? '#5f8e46' : '#5a3d27'; ctx.fillRect(point.x - 24, point.y - 10, 48, 20);
    for (let i = -18; i <= 18; i += 12) { ctx.strokeStyle = '#d0b36a'; ctx.beginPath(); ctx.moveTo(point.x + i, point.y - 10); ctx.lineTo(point.x + i, point.y + 10); ctx.stroke(); }
  } else if (node.type === 'cattle') {
    ctx.fillStyle = '#d8c7a5'; ctx.fillRect(point.x - 16, point.y - 22, 28, 15); ctx.beginPath(); ctx.arc(point.x + 15, point.y - 18, 8, 0, Math.PI * 2); ctx.fill();
  } else if (node.type === 'store') {
    ctx.fillStyle = '#8c5d31'; ctx.fillRect(point.x - 23, point.y - 26, 46, 26); ctx.fillStyle = '#d9bb72'; ctx.fillRect(point.x - 18, point.y - 22, 36, 7);
  } else if (node.type === 'reeds') {
    ctx.strokeStyle = '#8ca64b'; ctx.lineWidth = 3;
    for (let i = -15; i <= 15; i += 6) { ctx.beginPath(); ctx.moveTo(point.x + i, point.y); ctx.lineTo(point.x + i + 2, point.y - 27 - Math.abs(i % 4)); ctx.stroke(); }
  }
  ctx.restore();
}

const IsometricSettlement = () => {
  const storageOwner = localStorage.getItem('userId') || 'anonymous';
  const [serverActorId, setServerActorId] = useState(null);
  const authorityActorId = serverActorId || localStorage.getItem('eovNetworkUserId') || storageOwner;
  const worldNamespace = `world:${storageOwner}`;
  const worldStorageKey = `${STORAGE_KEY}:${storageOwner}`;
  const simulationStorageKey = `eov-settlement-simulation:${storageOwner}`;
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const chatInputRef = useRef(null);
  const frameRef = useRef(null);
  const visualPlayerRef = useRef({ x: INITIAL_WORLD.player.x, y: INITIAL_WORLD.player.y });
  const npcVisualsRef = useRef({});
  const cameraRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [recipientId, setRecipientId] = useState('');
  const movementLockRef = useRef(false);
  const walkToTileRef = useRef(null);
  const [world, setWorld] = useState(INITIAL_WORLD);
  const [simulation, setSimulation] = useState(() => initialSimulation());
  const [buildMode, setBuildMode] = useState(false);
  const [selectedType, setSelectedType] = useState('workshop');
  const [hoverTile, setHoverTile] = useState(null);
  const [selected, setSelected] = useState(null);
  const [savedAt, setSavedAt] = useState(null);
  const [serverSnapshot, setServerSnapshot] = useState(null);
  const [serverOwner, setServerOwner] = useState(null);
  const [serverError, setServerError] = useState(null);
  const [chatInput, setChatInput] = useState('');
  const [movementStatus, setMovementStatus] = useState('');
  const [actionReceipt, setActionReceipt] = useState(null);
  const [calibrationReadings, setCalibrationReadings] = useState('1.000, 1.004, 1.002');
  const [mealThermalRecord, setMealThermalRecord] = useState({ temperature: '82', minutes: '15' });
  const [repairConditionRecord, setRepairConditionRecord] = useState({ before: '0.30', after: '0.86' });
  const [extractionObservation, setExtractionObservation] = useState({ stockBefore: '10', observedYield: '2' });
  const [pumpDesign, setPumpDesign] = useState({ name: 'Founders lever pump', effortArm: '1.2', loadArm: '0.3', pistonDiameter: '0.12', stroke: '0.5', efficiency: '0.75' });
  const isOwner = serverOwner === true;
  const frontierView = useMemo(() => projectObservedFrontier(serverSnapshot, authorityActorId), [authorityActorId, serverSnapshot]);
  const activeMapSize = frontierView.connected ? frontierView.size : MAP_SIZE;
  const routeStatus = frontierView.route?.status === 'traveling'
    ? `Traveling ${frontierView.route.index}/${Math.max(1, frontierView.route.path.length - 1)} to ${frontierView.route.path.at(-1).join(',')}`
    : movementStatus;

  const settlementStats = useMemo(() => ({
    residents: serverSnapshot ? Object.keys(serverSnapshot.state?.npcs || {}).length + Object.keys(serverSnapshot.state?.players || {}).length : simulation.npcs.length + 1,
    structures: world.blueprints.length,
    activeProjects: world.blueprints.filter((item) => item.stage < 4).length,
  }), [serverSnapshot, simulation.npcs.length, world.blueprints]);

  const visibleResourceNodes = useMemo(() => {
    if (!serverSnapshot) return world.resourceNodes;
    const region = serverSnapshot.state?.players?.[authorityActorId]?.current_region || 'settlement';
    return Object.values(serverSnapshot.state?.resource_sites || {}).filter((site) => site.region === region && Array.isArray(site.location)).map((site) => ({
      ...site, x: site.location[0], y: site.location[1], readyTick: site.ready_tick,
      fedUntilTick: site.fed_until_tick, serverAuthoritative: true,
    }));
  }, [authorityActorId, serverSnapshot, world.resourceNodes]);

  useEffect(() => {
    if (!worldServerConfigured) return undefined;
    const controller = new AbortController();
    let active = true;
    let inFlight = false;
    const synchronize = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        let snapshot = await fetchWorldSnapshot(undefined, controller.signal);
        if (snapshot.viewer_id && !snapshot.state?.players?.[snapshot.viewer_id]) {
          await submitWorldAction({ type: 'join' }, snapshot.revision);
          snapshot = await fetchWorldSnapshot(undefined, controller.signal);
        }
        if (active && isRenderableServerSnapshot(snapshot)) {
          if (snapshot.viewer_id) {
            setServerActorId(snapshot.viewer_id);
            localStorage.setItem('eovNetworkUserId', snapshot.viewer_id);
          }
          if (typeof snapshot.viewer_is_owner === 'boolean') setServerOwner(snapshot.viewer_is_owner);
          setServerSnapshot(current => !current || snapshot.revision >= current.revision ? snapshot : current);
          const actor = snapshot.state?.players?.[snapshot.viewer_id || authorityActorId];
          if (actor?.location) setWorld((current) => ({ ...current, player: { ...current.player, x: actor.location[0], y: actor.location[1] } }));
          setServerError(null);
        } else if (active) {
          setServerError('World server returned an incomplete snapshot. Waiting to reconnect.');
        }
      } catch (error) {
        if (active && error.name !== 'AbortError') setServerError(error.message);
      } finally {
        inFlight = false;
      }
    };
    synchronize();
    const timer = window.setInterval(synchronize, 1000);
    return () => { active = false; controller.abort(); window.clearInterval(timer); };
  }, [authorityActorId]);

  useEffect(() => {
    localStorage.setItem(`eovLastRoute:${storageOwner}`, '/play');
    if (worldServerConfigured || !localPracticeEnabled) return undefined;
    let active = true;
    readDurable(worldNamespace, worldStorageKey, INITIAL_WORLD).then((saved) => {
      if (active && saved?.player && Array.isArray(saved.blueprints)) setWorld(ensureWorldState(saved));
    });
    readDurable(worldNamespace, simulationStorageKey, initialSimulation()).then((saved) => {
      if (!active || !saved?.clock || !Array.isArray(saved.npcs)) return;
      const caughtUp = catchUpSimulation(saved);
      setSimulation(caughtUp);
      writeDurable(worldNamespace, simulationStorageKey, caughtUp);
    });
    return () => { active = false; };
  }, [simulationStorageKey, storageOwner, worldNamespace, worldStorageKey]);

  useEffect(() => {
    if (worldServerConfigured || !localPracticeEnabled) return undefined;
    const timer = window.setInterval(() => {
      setSimulation((current) => {
        const next = advanceSimulation(current, 1);
        if (next.workOrder.stage > current.workOrder.stage) {
          const completed = STAGES[next.workOrder.stage - 1];
          const record = next.evidenceRecords?.[0];
          appendCausalEvent({ actionId: `${next.workOrder.id}:${completed.id}`, actorId: record?.actors?.join(',') || 'settlement_npcs', state: 'verified', intent: completed.label, location: `${completed.target[0]},${completed.target[1]}`, parentEventIds: [], inputs: record?.inputs || {}, outputs: { verifiedEffort: completed.effort, measurements: record?.measurements || {} }, evidence: [{ kind: 'persistent_tick_record', tick: next.clock.tick, tools: record?.tools || [], inspector: record?.inspector || null }], physicalEffect: Boolean(record?.physical) });
        }
        if (next.workOrder.status !== current.workOrder.status) {
          const lifecycle = next.workOrder.lifecycle.at(-1);
          appendCausalEvent({ actionId: `${next.workOrder.id}:lifecycle:${next.workOrder.status}`, actorId: lifecycle?.actor || 'settlement', state: next.workOrder.status, intent: `Advance workshop lifecycle to ${next.workOrder.status}`, location: '8,7', parentEventIds: [], inputs: next.workOrder.status === 'supplied' ? next.workOrder.supplied : {}, outputs: { status: next.workOrder.status }, evidence: [{ kind: lifecycle?.evidence || 'persistent_simulation_record', tick: next.clock.tick }], physicalEffect: ['supplied', 'performed', 'completed'].includes(next.workOrder.status) });
        }
        setWorld((currentWorld) => {
          let nextWorld = currentWorld;
          const nodes = currentWorld.resourceNodes.map((node) => {
            if (node.type === 'farm' && node.stage === 'growing' && node.readyTick <= next.clock.tick) return { ...node, stage: 'ripe', stock: node.capacity };
            if (node.type === 'cattle') return { ...node, wellbeing: Math.max(0, node.wellbeing - 0.04), stock: node.fedUntilTick >= next.clock.tick ? Math.min(node.capacity, node.stock + 0.03) : node.stock };
            return node;
          });
          nextWorld = { ...currentWorld, resourceNodes: nodes, player: { ...currentWorld.player, energy: Math.min(100, currentWorld.player.energy + 0.15) } };
          if (next.clock.tick % 8 === 0 && !currentWorld.communications.some((message) => message.tick === next.clock.tick && message.kind === 'autonomous')) {
            const speaker = next.npcs.slice().sort((a, b) => a.needs.belonging - b.needs.belonging || a.id.localeCompare(b.id))[0];
            const message = { id: crypto.randomUUID(), tick: next.clock.tick, speaker: speaker.name, speakerId: speaker.id, content: `${speaker.task.reason} I am going to ${speaker.task.label}.`, kind: 'autonomous' };
            nextWorld = { ...nextWorld, communications: [...currentWorld.communications, message].slice(-100) };
          }
          writeDurable(worldNamespace, worldStorageKey, nextWorld);
          return nextWorld;
        });
        writeDurable(worldNamespace, simulationStorageKey, next);
        return next;
      });
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [simulationStorageKey, worldNamespace, worldStorageKey]);

  const viewerRegion = serverSnapshot?.state?.players?.[serverSnapshot.viewer_id || authorityActorId]?.current_region || 'settlement';
  const authoritativeNpcs = serverSnapshot ? Object.values(serverSnapshot.state?.npcs || {}).filter((npc) => Array.isArray(npc.location) && (npc.current_region || 'settlement') === viewerRegion).map((npc, index) => ({ ...npc, x: npc.location[0], y: npc.location[1], color: ['#67e8f9', '#fbbf24', '#c084fc', '#fb7185', '#4ade80', '#a78bfa'][index % 6], schedule: { shiftStart: npc.schedule?.shift_start ?? 0, shiftEnd: npc.schedule?.shift_end ?? 24 }, needs: npc.needs || {}, competencies: npc.competencies || {}, task: { label: npc.intention || 'Observe', reason: npc.reason || 'No recorded intention.' } })) : simulation.npcs;

  const saveWorld = useCallback(async (nextWorld = world) => {
    const envelope = await writeDurable(worldNamespace, worldStorageKey, nextWorld);
    setSavedAt(new Date(envelope.savedAt));
  }, [world, worldNamespace, worldStorageKey]);

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    const now = performance.now();
    const nextNpcVisuals = {};
    const renderedNpcs = authoritativeNpcs.map((npc) => {
      const stepped = stepEntityMotion(npcVisualsRef.current[npc.id], { x: npc.x, y: npc.y }, now);
      nextNpcVisuals[npc.id] = stepped.motion;
      return { ...npc, x: stepped.position.x, y: stepped.position.y };
    });
    npcVisualsRef.current = nextNpcVisuals;
    canvas.dataset.visibleNpcCount = String(renderedNpcs.length);
    canvas.dataset.visibleNpcIds = renderedNpcs.map((npc) => npc.id).join(',');
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
    if (!localPracticeEnabled && !serverSnapshot) return;

    const frontierActive = frontierView.connected;
    const visualPlayer = visualPlayerRef.current;
    visualPlayer.x += (world.player.x - visualPlayer.x) * 0.22;
    visualPlayer.y += (world.player.y - visualPlayer.y) * 0.22;
    const camera = createCamera(width, height, visualPlayer, zoom);
    cameraRef.current = camera;
    canvas.dataset.cameraX = visualPlayer.x.toFixed(3);
    canvas.dataset.cameraY = visualPlayer.y.toFixed(3);
    const originX = 0;
    const originY = 0;
    const { minX, maxX, minY, maxY } = visibleBounds(camera, activeMapSize);
    ctx.save();
    ctx.translate(width / 2, height / 2);
    ctx.scale(camera.zoom, camera.zoom);
    ctx.translate(-(visualPlayer.x - visualPlayer.y) * TILE_W / 2, -(visualPlayer.x + visualPlayer.y) * TILE_H / 2);
    for (let sum = minX + minY; sum <= maxX + maxY; sum += 1) {
      for (let x = minX; x <= maxX; x += 1) {
        const y = sum - x;
        if (y < minY || y > maxY) continue;
        const point = worldToScreen(x, y, originX, originY);
        const observed = frontierActive ? frontierView.tiles[`${x},${y}`] : null;
        const road = !frontierActive && (x === 8 || y === 9);
        const checker = (x + y) % 2 === 0;
        const terrainColor = { grassland: '#304d3a', forest: '#173b2a', rocky: '#465057', wetland: '#253f42', water: '#123246' }[observed?.terrain];
        drawDiamond(ctx, point.x, point.y, frontierActive ? (observed ? terrainColor || '#294433' : '#071014') : road ? '#49545a' : checker ? '#304d3a' : '#294433', observed ? 'rgba(126,220,225,.16)' : 'rgba(0,0,0,.35)');
        if (observed?.excavationDepthCm) drawDiamond(ctx, point.x, point.y + 3, 'rgba(12,12,10,.68)', '#8a6842');
        if (observed?.preparedFoundation) drawDiamond(ctx, point.x, point.y - 2, 'rgba(194,166,102,.35)', '#d4af37');
        if (observed?.surface?.stock > 0) drawResource(ctx, point, { type: observed.surface.kind === 'tree' ? 'tree' : 'mineral', stock: observed.surface.stock });
        if (hoverTile?.x === x && hoverTile?.y === y) {
          drawDiamond(ctx, point.x, point.y, buildMode ? 'rgba(212,175,55,.42)' : 'rgba(103,232,249,.25)', '#d4af37');
        }

        const workshop = x === 8 && y === 7 ? { id: simulation.workOrder.id, x, y, type: 'workshop', stage: Math.min(4, simulation.workOrder.stage + 1), name: 'Measurement Workshop' } : null;
        const structure = !serverSnapshot ? world.blueprints.find((item) => item.x === x && item.y === y) || workshop : null;
        if (structure) {
          const spec = BUILDINGS[structure.type] || BUILDINGS.workshop;
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

        const resource = visibleResourceNodes.find((item) => item.x === x && item.y === y);
        if (resource) drawResource(ctx, point, resource);

      }
    }

    for (const npc of renderedNpcs) {
      const route = npc.route;
      if (route?.status === 'traveling' && Array.isArray(route.path)) {
        const remaining = route.path.slice(Math.max(0, Number(route.index) || 0));
        if (remaining.length > 1) {
          ctx.save();
          ctx.strokeStyle = 'rgba(212,175,55,.64)';
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 5]);
          ctx.beginPath();
          remaining.forEach(([x, y], index) => {
            const point = worldToScreen(x, y, originX, originY);
            if (index === 0) ctx.moveTo(point.x, point.y - 3);
            else ctx.lineTo(point.x, point.y - 3);
          });
          ctx.stroke();
          ctx.setLineDash([]);
          const [targetX, targetY] = remaining.at(-1);
          const targetPoint = worldToScreen(targetX, targetY, originX, originY);
          ctx.strokeStyle = 'rgba(240,217,133,.8)';
          ctx.beginPath();
          ctx.arc(targetPoint.x, targetPoint.y - 3, 8, 0, Math.PI * 2);
          ctx.stroke();
          ctx.restore();
        }
      }
      const point = worldToScreen(npc.x, npc.y, originX, originY);
      ctx.save();
      ctx.shadowColor = npc.color;
      ctx.shadowBlur = 12;
      ctx.fillStyle = npc.color;
      ctx.beginPath();
      ctx.arc(point.x, point.y - 24, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#0b1014';
      ctx.fillRect(point.x - 6, point.y - 16, 12, 19);
      const label = npc.name || npc.id;
      ctx.font = '10px JetBrains Mono, monospace';
      const labelWidth = ctx.measureText(label).width + 12;
      ctx.fillStyle = 'rgba(3,9,11,.9)';
      ctx.fillRect(point.x - labelWidth / 2, point.y - 48, labelWidth, 16);
      ctx.strokeStyle = 'rgba(126,220,225,.45)';
      ctx.strokeRect(point.x - labelWidth / 2, point.y - 48, labelWidth, 16);
      ctx.fillStyle = '#d8e7e4';
      ctx.textAlign = 'center';
      ctx.fillText(label, point.x, point.y - 37);
      ctx.restore();
    }

    const playerPoint = worldToScreen(visualPlayer.x, visualPlayer.y, originX, originY);
    ctx.fillStyle = '#f6d365';
    ctx.beginPath();
    ctx.arc(playerPoint.x, playerPoint.y - 27, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#4f46e5';
    ctx.fillRect(playerPoint.x - 7, playerPoint.y - 18, 14, 22);
    ctx.strokeStyle = '#f6d365';
    ctx.strokeRect(playerPoint.x - 10, playerPoint.y - 31, 20, 36);
    ctx.restore();
  }, [activeMapSize, authoritativeNpcs, buildMode, frontierView, hoverTile, serverSnapshot, simulation, visibleResourceNodes, world, zoom]);

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
      if (shouldToggleChat(event)) {
        event.preventDefault();
        setChatOpen((open) => !open);
        return;
      }
      if (event.target instanceof HTMLElement && (event.target.matches('input, textarea, select, button') || event.target.isContentEditable)) return;
      const key = event.key.toLowerCase();
      const delta = {
        w: [0, -1], arrowup: [0, -1],
        s: [0, 1], arrowdown: [0, 1],
        a: [-1, 0], arrowleft: [-1, 0],
        d: [1, 0], arrowright: [1, 0],
      }[key];
      if (!delta || buildMode) return;
      event.preventDefault();
      walkToTileRef.current?.({ x: clamp(world.player.x + delta[0], activeMapSize - 1), y: clamp(world.player.y + delta[1], activeMapSize - 1) });
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeMapSize, buildMode, world.player.x, world.player.y]);

  useEffect(() => {
    if (chatOpen) chatInputRef.current?.focus({ preventScroll: true });
  }, [chatOpen]);

  const eventToTile = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const sx = event.clientX - rect.left;
    const sy = event.clientY - rect.top;
    return tileAtPoint(cameraRef.current || createCamera(rect.width, rect.height, visualPlayerRef.current, zoom), sx, sy);
  };

  const handlePointerMove = (event) => {
    const tile = eventToTile(event);
    setHoverTile(tile.x >= 0 && tile.y >= 0 && tile.x < activeMapSize && tile.y < activeMapSize ? tile : null);
  };

  const walkToTile = async (target) => {
    if (movementLockRef.current || buildMode || (!localPracticeEnabled && !serverSnapshot)) return;
    movementLockRef.current = true;
    setMovementStatus(`Walking to ${target.x},${target.y}`);
    try {
      if (!worldServerConfigured) {
        setWorld((current) => ({ ...current, player: { ...current.player, x: clamp(target.x), y: clamp(target.y) } }));
        return;
      }
      let snapshot = serverSnapshot || await fetchWorldSnapshot();
      let position = snapshot.state?.players?.[authorityActorId]?.location;
      if (!position) {
        await submitWorldAction({ type: 'join', location: [world.player.x, world.player.y] }, snapshot.revision);
        snapshot = await fetchWorldSnapshot();
        position = snapshot.state?.players?.[authorityActorId]?.location || [world.player.x, world.player.y];
      }
      await submitWorldAction({ type: 'travel_route', destination: [target.x, target.y] }, snapshot.revision);
      snapshot = await fetchWorldSnapshot();
      if (!isRenderableServerSnapshot(snapshot)) throw new Error('World server returned an incomplete route snapshot');
      setServerSnapshot(snapshot);
      setMovementStatus(`Route accepted to ${target.x},${target.y}`);
      setServerError(null);
    } catch (error) {
      setServerError(error.message);
    } finally {
      movementLockRef.current = false;
      setMovementStatus('');
    }
  };
  walkToTileRef.current = walkToTile;

  const handleCanvasClick = async (event) => {
    const hoverTile = eventToTile(event);
    if (hoverTile.x < 0 || hoverTile.y < 0 || hoverTile.x >= activeMapSize || hoverTile.y >= activeMapSize) return;
    if ((!localPracticeEnabled || worldServerConfigured) && (!serverSnapshot || serverError)) return;
    const structure = !serverSnapshot && world.blueprints.find((item) => item.x === hoverTile.x && item.y === hoverTile.y);
    const npc = authoritativeNpcs.find((item) => item.x === hoverTile.x && item.y === hoverTile.y);
    const resources = visibleResourceNodes.filter((item) => item.x === hoverTile.x && item.y === hoverTile.y);
    const resource = resources[0];
    const workshop = hoverTile.x === 8 && hoverTile.y === 7
      ? (serverSnapshot
        ? { id: 'measurement-lab', name: 'Measurement laboratory', role: 'Canonical work station', sharedActionStation: true }
        : { id: simulation.workOrder.id, name: simulation.workOrder.title, simulationWorkOrder: true })
      : null;
    if (buildMode) {
      if (worldServerConfigured) {
        try {
          const surveyed = await submitWorldAction({ type: 'survey_frontier', location: [hoverTile.x, hoverTile.y] }, serverSnapshot?.revision);
          await submitWorldAction({ type: 'prepare_frontier_plot', location: [hoverTile.x, hoverTile.y] }, surveyed.revision);
          const refreshed = await fetchWorldSnapshot();
          setServerSnapshot(refreshed);
          setBuildMode(false);
          setServerError(null);
        } catch (error) { setServerError(error.message); }
        return;
      }
      if (structure || npc || resource || (world.player.x === hoverTile.x && world.player.y === hoverTile.y)) return;
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
    const selectedObject = resources.length > 1
      ? { ...resource, id: `resource-tile:${hoverTile.x},${hoverTile.y}`, name: `Resources at ${hoverTile.x},${hoverTile.y}`, resourceIds: resources.map((item) => item.id) }
      : resource || structure || npc || workshop || null;
    setSelected(selectedObject);
    setActionReceipt(null);
    if (resource) {
      if (serverSnapshot) {
        const response = await performAuthorityAction({ type: 'approach_site', site_id: resource.id });
        if (response?.result?.accepted === false) setActionReceipt(formatResourceReceipt(response.result, resource.name));
      } else {
        const approach = approachTileForSite(resource, world.player, null, activeMapSize);
        if (approach && (approach.x !== world.player.x || approach.y !== world.player.y)) await walkToTile(approach);
      }
    } else if (!selectedObject) {
      await walkToTile(hoverTile);
    }
  };

  const resetSettlement = () => {
    setWorld(INITIAL_WORLD);
    const nextSimulation = initialSimulation();
    setSimulation(nextSimulation);
    setSelected(null);
    saveWorld(INITIAL_WORLD);
    writeDurable(worldNamespace, simulationStorageKey, nextSimulation);
  };

  const toggleClock = () => {
    setSimulation((current) => {
      const next = { ...current, clock: { ...current.clock, paused: !current.clock.paused }, lastTickAt: Date.now() };
      writeDurable(worldNamespace, simulationStorageKey, next);
      return next;
    });
  };

  const performSkillAction = (domain) => {
    setSimulation((current) => {
      const result = playerAct(current, domain);
      if (result.ok) {
        writeDurable(worldNamespace, simulationStorageKey, result.state);
        appendCausalEvent({ actionId: `${current.workOrder.id}:${currentStage.id}:player:${current.clock.tick}`, actorId: localStorage.getItem('currentCharacterId') || `character-${storageOwner}`, state: 'in_progress', intent: currentStage.label, location: `${currentStage.target[0]},${currentStage.target[1]}`, parentEventIds: [], inputs: {}, outputs: { domain, verifiedEffort: result.state.workOrder.progress - current.workOrder.progress }, evidence: [{ kind: 'direct_player_action', tools: simulationEngine.ACTIONS[currentStage.action].tools }], physicalEffect: currentStage.action === 'assemble' || currentStage.action === 'survey' });
      }
      return result.state;
    });
  };

  const acceptNegotiatedOrder = () => {
    setSimulation((current) => {
      const result = acceptWorkOrder(current);
      if (!result.ok) return current;
      writeDurable(worldNamespace, simulationStorageKey, result.state);
      appendCausalEvent({ actionId: `${current.workOrder.id}:accept`, actorId: localStorage.getItem('currentCharacterId') || `character-${storageOwner}`, state: 'accepted', intent: 'Accept negotiated measurement workshop contract', location: 'settlement', parentEventIds: [], inputs: { terms: current.workOrder.negotiation.responses }, outputs: { status: 'accepted' }, evidence: [{ kind: 'three_party_negotiation' }], physicalEffect: false });
      return result.state;
    });
  };

  const chooseProductionPriority = (priority) => {
    setSimulation((current) => {
      const next = setProductionPriority(current, priority);
      writeDurable(worldNamespace, simulationStorageKey, next);
      appendCausalEvent({ actionId: `treasury-priority:${priority}:${current.clock.tick}`, actorId: localStorage.getItem('currentCharacterId') || `character-${storageOwner}`, state: 'accepted', intent: `Prioritize public ${priority} production`, location: 'settlement', parentEventIds: [], inputs: { requestedPriority: priority }, outputs: { productionPriority: priority }, evidence: [{ kind: 'owner_contract_choice' }], physicalEffect: false });
      return next;
    });
  };

  const endorseCivicPriority = async (priority) => {
    if (!serverSnapshot) return;
    try {
      await submitWorldAction({ type: 'endorse_priority', priority }, serverSnapshot.revision);
      setServerSnapshot(await fetchWorldSnapshot());
      setServerError(null);
    } catch (error) {
      setServerError(error.message);
    }
  };

  const performAuthorityAction = async (action) => {
    if (!serverSnapshot) return;
    try {
      const result = await submitWorldAction(action, serverSnapshot.revision);
      setServerSnapshot(await fetchWorldSnapshot());
      setServerError(result.result?.accepted === false ? result.result.reason : null);
      return result;
    } catch (error) {
      setServerError(error.message);
      return { result: { accepted: false, reason: error.message } };
    }
  };

  const proposeOwnerDirective = async (directive) => {
    if (!serverSnapshot) throw new Error('The persistent world is not connected');
    await submitOwnerDirective(directive, serverSnapshot.revision);
    setServerSnapshot(await fetchWorldSnapshot());
  };

  const proposePumpDesign = async (event) => {
    event.preventDefault();
    await performAuthorityAction({
      type: 'propose_invention', archetype: 'lever_pump', name: pumpDesign.name,
      specification: {
        effort_arm_m: Number(pumpDesign.effortArm), load_arm_m: Number(pumpDesign.loadArm),
        piston_diameter_m: Number(pumpDesign.pistonDiameter), stroke_m: Number(pumpDesign.stroke), efficiency: Number(pumpDesign.efficiency),
      },
      test_protocol: 'Measure ten strokes into a graduated vessel and compare observed volume with the SI prediction.',
      knowledge_sources: ['player dimensioned workshop design', 'settlement lever and piston reference'],
    });
  };

  const performSharedAction = async (operation, sharedActionId, extra = {}) => {
    await performAuthorityAction({ type: 'shared_action', operation, shared_action_id: sharedActionId, ...extra });
  };

  const proposeCalibration = async () => {
    const actionId = `player-calibration-${authorityActorId}-${Date.now()}`;
    await performSharedAction('propose', actionId, {
      action_type: 'calibrate_measurement_tool',
      intent: 'restore trustworthy settlement measurement',
      observations: ['Observed marked-measure drift at the measurement bench'],
    });
  };

  const executeSharedWork = async (record) => {
    const model = record.definition?.execution_model;
    const samples = model === 'thermal_batch'
      ? [{ temperature_c: Number(mealThermalRecord.temperature), duration_minutes: Number(mealThermalRecord.minutes) }]
      : model === 'condition_restoration'
        ? [{ condition_before: Number(repairConditionRecord.before), condition_after: Number(repairConditionRecord.after) }]
        : model === 'finite_site_extraction'
          ? [{ stock_before: Number(extractionObservation.stockBefore), observed_yield: Number(extractionObservation.observedYield) }]
        : calibrationReadings.split(',').map((value) => Number(value.trim())).filter(Number.isFinite).map((reading) => ({ reading }));
    await performSharedAction('execute', record.id, { samples });
  };

  const proposeCommunalMeal = async () => {
    const actionId = `player-meal-${authorityActorId}-${Date.now()}`;
    await performSharedAction('propose', actionId, {
      action_type: 'prepare_communal_meal',
      intent: 'produce an independently verified communal meal',
      observations: ['Observed unmet safe-meal demand in the settlement record'],
    });
  };

  const interactWithResource = async (interaction) => {
    const node = visibleResourceNodes.find((item) => item.id === interaction?.siteId)
      || visibleResourceNodes.find((item) => item.id === selected?.id);
    if (!node) return;
    if (serverSnapshot) {
      const inventory = serverSnapshot.state.players?.[authorityActorId]?.inventory || {};
      let siteAction = interaction?.operation
        ? { operation: interaction.operation, ...(interaction.item ? { item: interaction.item } : {}) }
        : operationForSite(node, inventory, serverSnapshot.tick);
      if (node.type === 'well' && node.progress >= 3 && !node.installed_pump) {
        const availablePump = Object.values(serverSnapshot.state.technology?.tool_catalog || {}).find((tool) => tool.archetype === 'lever_pump' && tool.available_units > 0);
        if (availablePump) siteAction = { operation: 'install_pump', design_id: availablePump.id };
      }
      if (!siteAction.operation || (siteAction.operation === 'checkout' && !siteAction.item)) { setServerError('No currently available site operation.'); return; }
      const response = await performAuthorityAction({ type: 'interact_site', site_id: node.id, ...siteAction });
      setActionReceipt(formatResourceReceipt(response?.result, node.name));
      return;
    }
    const distance = Math.abs(world.player.x - node.x) + Math.abs(world.player.y - node.y);
    if (distance > 1) { setServerError(`Move beside ${node.name} before interacting.`); return; }
    const next = ensureWorldState(structuredClone(world));
    const target = next.resourceNodes.find((item) => item.id === node.id);
    const inventory = next.player.inventory;
    let action = ''; let outputs = {}; let cost = 4;
    if (target.type === 'store') {
      const requested = interaction?.item || Object.keys(target.stock).find((item) => target.stock[item] > 0);
      if (!requested) { setServerError('Dev has no unissued starter supplies for you.'); return; }
      const quantity = interaction?.quantity || (['seed', 'feed'].includes(requested) ? 4 : 1);
      const checkout = checkoutLocalStoreItem(target, inventory, requested, quantity);
      if (!checkout.accepted) { setServerError(`${requested} stock is below the checkout quantity.`); return; }
      action = `checked out ${requested} from ${target.clerk}`; outputs = checkout.outputs; cost = 0;
    } else if (target.type === 'tree') {
      if (!inventory.axe) { setServerError('An axe is required. Dev’s tool counter can issue one.'); return; }
      if (target.stock < 1) { setServerError('This tree is depleted; its stump remains part of the world.'); return; }
      const amount = Math.min(2, target.stock); target.stock -= amount; inventory.timber = (inventory.timber || 0) + amount; action = 'chopped timber'; outputs = { timber: amount };
    } else if (target.type === 'mineral') {
      if (!inventory.pick) { setServerError('A pick is required.'); return; }
      if (target.stock < 1) { setServerError('No exposed mineral remains here.'); return; }
      target.stock -= 1; inventory.stone = (inventory.stone || 0) + 1; inventory.ore = (inventory.ore || 0) + (target.stock % 3 === 0 ? 1 : 0); action = 'mined the exposed seam'; outputs = { stone: 1, ore: target.stock % 3 === 0 ? 1 : 0 }; cost = 6;
    } else if (target.type === 'well') {
      if (target.progress < 3) {
        if (!inventory.shovel) { setServerError('A shovel is required to dig the well.'); return; }
        target.progress += 1; if (target.progress === 3) target.stock = target.capacity; action = `dug well stage ${target.progress}/3`; outputs = { excavation: 1, water_access: target.progress === 3 }; cost = 7;
      } else {
        if (!inventory.bucket) { setServerError('A bucket is required to draw water.'); return; }
        inventory.water = (inventory.water || 0) + 3; target.stock = Math.max(0, target.stock - 3); action = 'drew water from the completed well'; outputs = { water: 3 };
      }
    } else if (target.type === 'farm') {
      if (!inventory.farm_tools) { setServerError('Farm tools are required.'); return; }
      if (target.stage === 'untilled') { target.stage = 'tilled'; action = 'tilled the farm plot'; outputs = { prepared_soil: 1 }; }
      else if (target.stage === 'tilled') {
        if (!inventory.seed) { setServerError('Seed is required.'); return; }
        inventory.seed -= 1; target.stage = 'growing'; target.readyTick = simulation.clock.tick + 12; action = 'sowed the farm plot'; outputs = { crop_due_tick: target.readyTick };
      } else if (target.stage === 'growing') { setServerError(`Crops are growing until tick ${target.readyTick}.`); return; }
      else { inventory.raw_food = (inventory.raw_food || 0) + target.stock; outputs = { raw_food: target.stock }; target.stock = 0; target.stage = 'untilled'; target.readyTick = null; action = 'harvested the farm plot'; }
    } else if (target.type === 'cattle') {
      if (inventory.feed > 0 && target.fedUntilTick < simulation.clock.tick) { inventory.feed -= 1; target.fedUntilTick = simulation.clock.tick + 16; target.wellbeing = Math.min(100, target.wellbeing + 12); action = 'fed and checked the cattle'; outputs = { wellbeing: target.wellbeing }; }
      else if (inventory.bucket && target.stock >= 1) { target.stock -= 1; inventory.milk = (inventory.milk || 0) + 1; action = 'milked a cared-for animal'; outputs = { milk: 1 }; }
      else { setServerError('The cattle need feed, time, and a bucket before producing more milk.'); return; }
    }
    if (next.player.energy < cost) { setServerError('You are too exhausted; rest before continuing.'); return; }
    next.player.energy -= cost;
    next.communications = [...next.communications, { id: crypto.randomUUID(), tick: simulation.clock.tick, speaker: 'World record', content: `${localStorage.getItem('username') || 'Player'} ${action}.`, kind: 'action' }].slice(-100);
    setWorld(next); setSelected(target); saveWorld(next); setServerError(null);
    const inventoryKeys = new Set(['axe', 'pick', 'shovel', 'bucket', 'wrench', 'farm_tools', 'seed', 'feed', 'timber', 'stone', 'ore', 'water', 'raw_food', 'milk']);
    const inventoryDelta = Object.fromEntries(Object.entries(outputs).filter(([key]) => inventoryKeys.has(key)));
    const custody = Object.keys(inventoryDelta).length ? 'actor_inventory' : 'site';
    setActionReceipt(formatResourceReceipt({
      accepted: true, status: 'completed', custody, operation: action,
      inventory_delta: inventoryDelta,
      site_delta: custody === 'site' ? outputs : {},
      energy: next.player.energy,
    }, target.name));
    appendCausalEvent({ actionId: `resource:${target.id}:${simulation.clock.tick}:${action}`, actorId: localStorage.getItem('currentCharacterId') || 'unknown', state: 'performed', intent: action, location: `${target.x},${target.y}`, parentEventIds: [], inputs: { toolAccess: Object.keys(inventory).filter((key) => ['axe', 'pick', 'shovel', 'bucket', 'farm_tools'].includes(key) && inventory[key]) }, outputs, evidence: [{ kind: 'direct_isometric_interaction', tick: simulation.clock.tick }], physicalEffect: target.type !== 'store' });
  };

  const sendProximityMessage = async (event) => {
    event.preventDefault();
    const content = chatInput.trim();
    if (!content || chatBusy) return;
    if (worldServerConfigured) {
      setChatBusy(true);
      try {
        if (!serverSnapshot || serverError) throw new Error('Reconnect to the persistent world before speaking.');
        const effectiveRecipient = nearbyResidents(serverSnapshot).some(resident => resident.id === recipientId) ? recipientId : '';
        const response = await performAuthorityAction(speechAction(serverSnapshot, content, effectiveRecipient));
        if (response?.result?.accepted) setChatInput('');
      } catch (error) { setServerError(error.message); }
      finally { setChatBusy(false); }
      return;
    }
    setChatInput('');
    const nearby = simulation.npcs.filter((npc) => Math.abs(npc.x - world.player.x) + Math.abs(npc.y - world.player.y) <= 4).sort((a, b) => a.id.localeCompare(b.id));
    const messages = [{ id: crypto.randomUUID(), tick: simulation.clock.tick, speaker: localStorage.getItem('username') || 'Player', content, kind: 'player' }];
    for (const npc of nearby.slice(0, 2)) {
      const reply = fallbackNpcReply(npc, content);
      messages.push({ id: crypto.randomUUID(), tick: simulation.clock.tick, speaker: npc.name, content: reply, kind: 'reply' });
    }
    if (!nearby.length) messages.push({ id: crypto.randomUUID(), tick: simulation.clock.tick, speaker: 'System', content: 'Nobody is close enough to hear you.', kind: 'system' });
    const next = { ...world, communications: [...world.communications, ...messages].slice(-100) };
    setWorld(next); saveWorld(next);
  };

  const currentStage = STAGES[simulation.workOrder.stage];
  const selectedView = authoritativeNpcs.find((npc) => npc.id === selected?.id) || visibleResourceNodes.find((node) => node.id === selected?.id) || selected;
  const listeners = nearbyResidents(serverSnapshot);
  const selectedResource = visibleResourceNodes.find((node) => node.id === selected?.id)
    || visibleResourceNodes.find((node) => selected?.resourceIds?.includes(node.id));
  const selectedTileResources = selectedResource
    ? visibleResourceNodes.filter((node) => node.x === selectedResource.x && node.y === selectedResource.y)
    : [];
  const selectedMaintenanceOrder = serverSnapshot?.state.institutions?.governance?.maintenance_orders?.find((order) => order.site_id === selectedResource?.id && order.status === 'open');
  const activeClock = serverSnapshot?.state?.clock || simulation.clock;
  const activePlayer = serverSnapshot?.state.players?.[authorityActorId] || world.player;
  const selectedResourceOptions = resourceInteractionOptions(
    visibleResourceNodes,
    selectedResource ? { x: selectedResource.x, y: selectedResource.y } : null,
    activePlayer.inventory || {},
    serverSnapshot?.tick,
  );
  const activeMinute = Number.isFinite(activeClock?.minute) ? activeClock.minute : 0;
  const worldTime = `${String(Math.floor(activeMinute / 60)).padStart(2, '0')}:${String(activeMinute % 60).padStart(2, '0')}`;
  const visibleMessages = serverSnapshot?.state.communications?.messages || world.communications;
  const visibleResidents = frontierView.connected
    ? authoritativeNpcs.filter((npc) => Boolean(frontierView.tiles[`${Math.floor(npc.x)},${Math.floor(npc.y)}`]))
    : authoritativeNpcs;
  const sharedActions = Object.values(serverSnapshot?.state.shared_actions?.records || {}).sort((a, b) => String(a.id).localeCompare(String(b.id)));
  const activeSharedDemand = (serverSnapshot?.state.shared_actions?.demands || []).find((demand) => demand.status !== 'resolved');
  const measurementCompetence = activePlayer.competency_records?.measurement?.demonstrated || 0;
  const cookingCompetence = activePlayer.competency_records?.cooking?.demonstrated || 0;
  const atMeasurementLab = (activePlayer.current_region || 'settlement') === 'settlement'
    && Math.abs((activePlayer.location?.[0] ?? -99) - 8) + Math.abs((activePlayer.location?.[1] ?? -99) - 7) <= 1;

  return (
    <div className="iso-shell">
      <header className="iso-header">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/select-mode')} aria-label="Back to modes"><ArrowLeft /></Button>
          <div>
            <p className="iso-kicker">ECHOES OF VIRTUALITY</p>
            <h1>Founders' Settlement</h1>
          </div>
        </div>
        <div className="iso-stats">
          <span><Clock3 size={15} /> {worldTime} · tick {serverSnapshot?.tick ?? simulation.clock.tick}</span>
          <span><Users size={15} /> {settlementStats.residents} residents</span>
          <Button variant="outline" onClick={() => navigate('/village')}>Story chat</Button>
          <Button variant="ghost" onClick={() => navigate('/settings')}>Settings</Button>
        </div>
      </header>

      <main className="iso-main">
        <section className="iso-viewport" aria-label="Isometric settlement viewport">
          <canvas ref={canvasRef} onMouseMove={handlePointerMove} onMouseLeave={() => setHoverTile(null)} onClick={handleCanvasClick} />
          <div className="iso-controls">
            {localPracticeEnabled && !worldServerConfigured && <>
            <Button variant="outline" disabled={Boolean(serverSnapshot)} onClick={toggleClock}>{serverSnapshot ? <Clock3 size={16} /> : simulation.clock.paused ? <Play size={16} /> : <Pause size={16} />} {serverSnapshot ? 'Server runclock' : simulation.clock.paused ? 'Resume' : 'Pause'}</Button>
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
            </>}
            {serverError && <span role="status">{serverError}</span>}
            {routeStatus && <span role="status">{routeStatus}</span>}
          </div>
          <div className="iso-camera-controls" aria-label="Map controls">
            <Button variant="outline" aria-label="Zoom out" disabled={zoom <= 0.5} onClick={() => setZoom(value => clampZoom(value - 0.25))}>−</Button>
            <output aria-label="Map zoom">{Math.round(zoom * 100)}%</output>
            <Button variant="outline" aria-label="Zoom in" disabled={zoom >= 1.75} onClick={() => setZoom(value => clampZoom(value + 0.25))}>+</Button>
            <span aria-label="Player position">{world.player.x}, {world.player.y}</span>
            <small>Click to travel · WASD / arrows · camera follows you</small>
          </div>
          <Button
            className="iso-chat-toggle"
            variant={chatOpen ? 'default' : 'outline'}
            onClick={() => setChatOpen((open) => !open)}
            aria-expanded={chatOpen}
            aria-controls="iso-proximity-chat"
            aria-label={chatOpen ? 'Close chat (T)' : 'Open chat (T)'}
          ><MessageCircle size={16} /> Chat <kbd>T</kbd></Button>
          {chatOpen && <div className="iso-chat-drawer" id="iso-proximity-chat" aria-label="Proximity chat">
            <div className="iso-chat-drawer-heading">
              <div><span className="iso-kicker">LOCAL VOICE</span><h2>Nearby conversation</h2></div>
              <Button variant="ghost" size="icon" onClick={() => setChatOpen(false)} aria-label="Close chat"><span aria-hidden="true">×</span></Button>
            </div>
            {serverSnapshot && <select aria-label="Speak to" value={listeners.some(r => r.id === recipientId) ? recipientId : ''} onChange={event => setRecipientId(event.target.value)}>
              <option value="">Nearest resident{listeners[0] ? ` · ${listeners[0].name}` : ''}</option>
              {listeners.map(resident => <option key={resident.id} value={resident.id}>{resident.name}</option>)}
            </select>}
            <div className="iso-chat-log" aria-live="polite">
              {visibleMessages.slice(-10).map((message) => <article key={message.id}><b>{message.speaker}</b><span>{message.content}</span><small>tick {message.tick} · {message.kind}</small></article>)}
              {!visibleMessages.length && <p>No audible speech recorded yet. Nearby residents may speak without being prompted.</p>}
            </div>
            <form onSubmit={sendProximityMessage}>
              <input ref={chatInputRef} value={chatInput} onChange={(event) => setChatInput(event.target.value)} disabled={chatBusy || ((!localPracticeEnabled || worldServerConfigured) && (!serverSnapshot || Boolean(serverError)))} maxLength={500} placeholder="Say hello or ask about work…" aria-label="Proximity chat message" />
              <Button type="submit" disabled={chatBusy || !chatInput.trim() || ((!localPracticeEnabled || worldServerConfigured) && !serverSnapshot)}>{chatBusy ? 'Sending…' : 'Speak'}</Button>
            </form>
          </div>}
          {!localPracticeEnabled && !serverSnapshot && <div className="iso-connection-overlay" role="status">
            <h2>Waiting for your persistent world</h2>
            <p>{serverError || (worldServerConfigured ? 'Connecting…' : 'Choose a world server in Settings, then sign in to join.')}</p>
            <Button onClick={() => navigate('/settings')}>Connection settings</Button>
            <Button variant="outline" onClick={() => navigate('/auth')}>Sign in</Button>
            <BuildWatermark />
          </div>}
        </section>

        <aside className="iso-sidebar">
          {worldServerConfigured && (
            <details className={`iso-server-authority ${serverSnapshot ? 'connected' : 'offline'}`}>
              <summary>Settlement status &amp; work</summary>
              <p className="iso-kicker">MULTIPLAYER AUTHORITY</p>
              <h2>{serverSnapshot ? 'Persistent server connected' : 'Waiting for world server'}</h2>
              {serverSnapshot ? <>
                <p>Revision {serverSnapshot.revision} · Tick {serverSnapshot.tick} · {Object.keys(serverSnapshot.state.players).length} connected player records</p>
                <strong>{serverSnapshot.state.event.title}</strong>
                <span>Phase: {serverSnapshot.state.event.priorities[serverSnapshot.state.event.phase]?.replace(/_/g, ' ') || 'Settlement life'}</span>
                {serverSnapshot.state.institutions?.council?.current_initiative && <>
                  <strong>{serverSnapshot.state.institutions.council.current_initiative.id}</strong>
                  <span>{serverSnapshot.state.institutions.council.current_initiative.status} · {serverSnapshot.state.institutions.council.current_initiative.reason}</span>
                </>}
                <div className="iso-priority">
                  <span>Endorse the council's next evidence review</span>
                  <div>{['sanitation', 'storage', 'water', 'food'].map((priority) => <Button key={priority} variant="outline" onClick={() => endorseCivicPriority(priority)}>{priority}</Button>)}</div>
                </div>
                {(serverSnapshot.state.institutions?.council?.agenda || []).slice(0, 4).map((item) => <small key={item.priority}>{item.priority}: pressure {item.pressure}</small>)}
                {serverSnapshot.state.players?.[authorityActorId] && (() => {
                  const player = serverSnapshot.state.players[authorityActorId];
                  const currentRegion = player.current_region || 'settlement';
                  const region = serverSnapshot.state.environment?.regions?.[currentRegion];
                  return <article>
                    <b>Expedition · {region?.name || currentRegion}</b>
                    <span>Discovered: {(player.discovered_regions || ['settlement']).map((id) => serverSnapshot.state.environment?.regions?.[id]?.name || id).join(', ')}</span>
                    <div className="iso-priority">
                      <span>{currentRegion === 'settlement' ? 'Reach a map boundary, then depart' : 'Available paths'}</span>
                      <div>{(region?.adjacent || []).map((target) => <Button key={target} variant="outline" onClick={() => performAuthorityAction({ type: 'explore_region', region: target })}>{serverSnapshot.state.environment.regions[target].name}</Button>)}</div>
                    </div>
                    {currentRegion !== 'settlement' && <div className="iso-priority">
                      <span>Observable materials</span>
                      <div>{Object.entries(region?.stocks || {}).filter(([, amount]) => amount > 0).map(([resource, amount]) => <Button key={resource} variant="outline" onClick={() => performAuthorityAction({ type: 'gather_material', resource, amount: 1 })}>{resource} ({amount})</Button>)}</div>
                    </div>}
                  </article>;
                })()}
                <article>
                  <b>Resource access · {serverSnapshot.state.institutions?.governance?.resource_access?.mode || 'open_stores'}</b>
                  {serverSnapshot.state.institutions?.governance?.resource_access?.proposal && <span>{serverSnapshot.state.institutions.governance.resource_access.proposal.status}: {serverSnapshot.state.institutions.governance.resource_access.proposal.rationale}</span>}
                  {serverSnapshot.state.institutions?.governance?.resource_access?.mode === 'recorded_checkout' && <div className="iso-priority">
                    <span>Meeting-hall checkout</span>
                    <div>{['tools', 'containers', 'timber'].map((resource) => <Button key={resource} variant="outline" onClick={() => performAuthorityAction({ type: 'checkout_resource', resource, amount: 1, purpose: 'player-directed settlement work' })}>{resource}</Button>)}</div>
                  </div>}
                  {Object.entries(serverSnapshot.state.players?.[authorityActorId]?.inventory || {}).filter(([, amount]) => amount > 0).map(([resource, amount]) => <small key={resource}>Held: {amount} {resource}</small>)}
                </article>
                <article>
                  <b>Resident survival · {serverSnapshot.state.resources.safe_meals} safe meals</b>
                  <span>{(serverSnapshot.state.survival?.meal_history || []).length} recorded meals · {(serverSnapshot.state.survival?.rest_history || []).length} rest records · {serverSnapshot.state.cooking?.waste_portions || 0} spoiled portions</span>
                  {(serverSnapshot.state.survival?.shortages || []).filter((item) => item.status === 'unresolved').map((item) => <small key={item.id}>{item.kind.replaceAll('_', ' ')} shortage affects {item.affected.join(', ')}</small>)}
                  {(serverSnapshot.state.cooking?.work_orders || []).slice().reverse().slice(0, 3).map((order) => <small key={order.id}>{order.id}: {order.status.replaceAll('_', ' ')} · {order.portions} portions{order.missing ? ` · missing ${Object.entries(order.missing).map(([item, amount]) => `${amount} ${item}`).join(', ')}` : ''}</small>)}
                  {(serverSnapshot.state.cooking?.meal_batches || []).slice().reverse().slice(0, 3).map((batch) => <small key={batch.id}>{batch.id}: {batch.status.replaceAll('_', ' ')} · {batch.remaining_portions || 0}/{batch.portions} portions{batch.expires_tick ? ` · expires tick ${batch.expires_tick}` : ''}</small>)}
                  {serverSnapshot.state.cooking?.preservation_program && <small>Preservation learning: {serverSnapshot.state.cooking.preservation_program.method} · {serverSnapshot.state.cooking.preservation_program.status.replaceAll('_', ' ')}{serverSnapshot.state.cooking.preservation_program.shelf_life_gain_ticks ? ` · +${serverSnapshot.state.cooking.preservation_program.shelf_life_gain_ticks} shelf-life ticks` : ''}{Object.keys(serverSnapshot.state.cooking.preservation_program.missing || {}).length ? ` · missing ${Object.entries(serverSnapshot.state.cooking.preservation_program.missing).map(([item, amount]) => `${amount} ${item}`).join(', ')}` : ''}</small>}
                </article>
                <AuthoritativeWorkPanel state={serverSnapshot.state} />
                {(serverSnapshot.state.institutions?.governance?.checkouts || []).filter((item) => item.borrower === authorityActorId && ['active', 'overdue'].includes(item.status)).map((item) => <article key={item.id}>
                  <b>{item.id} · {item.status}</b>
                  <span>Due tick {item.due_tick} · {item.purpose}</span>
                  {Object.entries(item.remaining).filter(([, amount]) => amount > 0).map(([resource, amount]) => <Button key={resource} variant="outline" onClick={() => performAuthorityAction({ type: 'return_checkout', checkout_id: item.id, resource, amount })}>Return {amount} {resource}</Button>)}
                </article>)}
                {(serverSnapshot.state.institutions?.justice?.bounties || []).filter((bounty) => bounty.status === 'active').map((bounty) => <article key={bounty.id}>
                  <b>{bounty.id} · {bounty.provisional_reward} provisional CU</b>
                  <span>Restitution recovery for {bounty.subject}</span>
                  {!bounty.assignee && <Button variant="outline" onClick={() => performAuthorityAction({ type: 'accept_bounty', bounty_id: bounty.id })}>Accept public duty</Button>}
                  {bounty.assignee?.id === authorityActorId && !bounty.contact && <Button variant="outline" onClick={() => performAuthorityAction({ type: 'request_restitution', bounty_id: bounty.id })}>Request restitution here</Button>}
                  <small>{bounty.assignee ? `Assigned to ${bounty.assignee.id}` : 'Open equally to player or AI recovery workers'}</small>
                </article>)}
                {(serverSnapshot.state.institutions?.justice?.cases || []).filter((item) => item.accused === authorityActorId && ['restitution_due', 'bounty_active'].includes(item.status)).map((item) => <article key={item.id}>
                  <b>{item.id} · {item.status}</b>
                  {Object.entries(item.restitution || {}).filter(([, amount]) => amount > 0).map(([resource, amount]) => <Button key={resource} variant="outline" onClick={() => performAuthorityAction({ type: 'return_resource', case_id: item.id, resource, amount })}>Return {amount} {resource}</Button>)}
                </article>)}
                <small>The server owns time, NPC decisions, state revisions, and catch-up. This client is a synchronized view.</small>
              </> : <><p>{serverError || 'Connecting…'}</p><small>{worldServerUrl}</small></>}
            </details>
          )}
          {serverSnapshot && <details className="iso-resident-roster" open>
            <summary><Users size={14} /> Resident activity <span>{visibleResidents.length} nearby</span></summary>
            <div className="iso-resident-list">
              {visibleResidents.map((resident) => {
                const traveling = resident.route?.status === 'traveling';
                const status = traveling ? `Walking to ${resident.route.destination_name || 'a nearby place'}` : resident.task?.label || 'Choosing an intention';
                return <button key={resident.id} type="button" className={selected?.id === resident.id ? 'selected' : ''} onClick={() => setSelected(resident)} aria-label={`Inspect ${resident.name}`}>
                  <span className="iso-resident-avatar" style={{ '--resident-tint': resident.color }}>{resident.name?.slice(0, 1) || '?'}</span>
                  <span className="iso-resident-copy"><strong>{resident.name}</strong><small>{status}</small><small>{Math.round(resident.x)}, {Math.round(resident.y)} · {resident.role || 'resident'}</small></span>
                  <span className={`iso-resident-state ${traveling ? 'traveling' : ''}`}>{traveling ? 'MOVING' : 'HERE'}</span>
                </button>;
              })}
              {!visibleResidents.length && <p className="iso-roster-empty">No residents are within the currently observed area.</p>}
            </div>
          </details>}
          {localPracticeEnabled && !worldServerConfigured && <>
          <div className="iso-simulation-status">
            <p className="iso-kicker">PERSISTENT SETTLEMENT</p>
            <h2>{simulation.workOrder.title}</h2>
            <div className="iso-work-summary">
              <span>{simulation.workOrder.status}</span>
              <strong>{simulation.workOrder.status === 'proposed' ? 'NPC terms pending' : simulation.workOrder.status === 'negotiated' ? 'Terms ready for acceptance' : simulation.workOrder.status === 'accepted' ? 'Supplying worksite' : simulation.workOrder.status === 'performed' ? 'Independent inspection' : simulation.workOrder.status === 'inspected' ? 'Closing evidence record' : currentStage?.label || 'Commissioned'}</strong>
              <div className="iso-progress"><i style={{ width: `${currentStage ? Math.min(100, (simulation.workOrder.progress / currentStage.effort) * 100) : 100}%` }} /></div>
              <small>{simulation.workOrder.status === 'supplied' && currentStage ? `${simulation.workOrder.progress.toFixed(1)} / ${currentStage.effort} verified effort` : simulation.workOrder.status === 'performed' ? `${simulation.workOrder.inspectionProgress.toFixed(1)} / 20 inspection evidence` : `${simulation.workOrder.lifecycle.length} lifecycle records`}</small>
            </div>
            <div className="iso-lifecycle">
              {['proposed', 'negotiated', 'accepted', 'supplied', 'performed', 'inspected', 'completed'].map((status) => <span key={status} className={simulation.workOrder.lifecycle.some((entry) => entry.status === status) ? 'done' : ''}><CheckCircle2 size={10} /> {status}</span>)}
            </div>
            <div className="iso-negotiation">
              {simulation.workOrder.negotiation.responses.map((response) => <article key={response.npcId}><b>{response.actor}</b><span>{response.condition}</span><small>{response.domain} · requested {response.requestedRate} provisional CU</small></article>)}
            </div>
            {simulation.workOrder.status === 'negotiated' && <Button className="iso-accept-order" onClick={acceptNegotiatedOrder}>Accept recorded terms</Button>}
            {(simulation.workOrder.status === 'accepted' || simulation.workOrder.status === 'supplied') && <div className="iso-supplies">{Object.entries(simulation.workOrder.requirements).map(([material, required]) => <span key={material}>{material}<b>{simulation.workOrder.supplied[material]} / {required}</b></span>)}</div>}
            <div className="iso-resources">
              {Object.entries(simulation.resources).map(([name, amount]) => <span key={name}><Package size={11} /> {name} <b>{amount}</b></span>)}
            </div>
            <small className="iso-cu">Provisional value: {simulation.workOrder.provisionalCU} CU · not issued</small>
          </div>

          <div className="iso-skill-actions">
            <p className="iso-kicker">PARTICIPATE</p>
            <div>
              {['measurement', 'logistics', 'engineering', 'science'].map((domain) => (
                <Button key={domain} variant="outline" disabled={!currentStage || currentStage.domain !== domain || simulation.workOrder.status !== 'supplied'} onClick={() => performSkillAction(domain)}>
                  {domain}
                </Button>
              ))}
            </div>
            <small>Only the competency required by the active stage can produce verified progress.</small>
          </div>

          </>}
          {serverSnapshot && <details className="iso-research-panel"><summary>Workshop &amp; evidence</summary>
            <p className="iso-kicker">MEASUREMENT LAB</p>
            <h2>Canonical production work</h2>
            <p>Every participant uses the same proposal, reservation, execution, verification, and commissioning rules. Physical presence determines which instruments can be perceived.</p>
            <article>
              <b>Marked measure · {Math.round((serverSnapshot.state.shared_actions?.tools?.marked_measure?.condition || 0) * 100)}% condition</b>
              <span>{activeSharedDemand ? `${activeSharedDemand.status.replaceAll('_', ' ')} · ${activeSharedDemand.reason || activeSharedDemand.cause?.condition}` : 'No unresolved calibration demand'}</span>
              <small>Your demonstrated measurement competence: {measurementCompetence.toFixed(2)} · laboratory perception: {atMeasurementLab ? 'available' : 'out of range'}</small>
              <Button variant="outline" onClick={proposeCalibration}>Propose observed calibration work</Button>
              <Button variant="outline" onClick={proposeCommunalMeal}>Propose observed communal meal</Button>
              <small>Your demonstrated cooking competence: {cookingCompetence.toFixed(2)} · meal safety still requires a different qualified inspector.</small>
            </article>
            {sharedActions.map((record) => <article key={record.id} data-testid="shared-action-record">
              <b>{record.id} · {String(record.state).replaceAll('_', ' ')}</b>
              {record.private ? <span>Detailed evidence is outside your current perspective.</span> : <>
                <span>{record.intent} · performer {record.actor_id}{record.verifier_id ? ` · verifier ${record.verifier_id}` : ''}</span>
                <small>{(record.observations || []).join('; ')}{record.output?.sample_count ? record.definition?.execution_model === 'thermal_batch' ? ` · safety ${record.output.safety} · peak ${record.output.peak_temperature_c}°C` : ` · ${record.output.sample_count} samples · spread ${record.output.spread}` : ''}</small>
                {record.definition?.execution_model === 'finite_site_extraction' && record.output?.stock_before != null && <small>Finite stock {record.output.stock_before} → {record.output.stock_after} · yield {record.output.yield} · observed {record.output.observed_yield} · conserved {record.output.conserved ? 'yes' : 'no'} · actor custody pending transport</small>}
                {record.output?.learning && <small>Instruction: theory {record.output.learning.theory} · observation {record.output.learning.observation} · procedure {record.output.learning.procedure} · demonstrated {record.output.learning.demonstrated_after} · verified practice still required</small>}
                {record.target_id === authorityActorId && record.state === 'awaiting_acceptances' && <div className="iso-priority"><Button variant="outline" onClick={() => performSharedAction('learner_accept', record.id)}>Accept instruction</Button><Button variant="ghost" onClick={() => performSharedAction('learner_refuse', record.id)}>Refuse instruction</Button></div>}
                {record.actor_id === authorityActorId && record.state === 'proposed' && <div className="iso-priority"><Button variant="outline" onClick={() => performSharedAction(record.definition?.execution_model === 'instruction_session' ? 'instructor_accept' : 'accept', record.id)}>Accept</Button><Button variant="ghost" onClick={() => performSharedAction('refuse', record.id)}>Refuse</Button></div>}
                {record.actor_id === authorityActorId && record.state === 'accepted' && <div className="iso-priority"><Button variant="outline" onClick={() => performSharedAction('reserve', record.id)}>Reserve required custody</Button><Button variant="ghost" onClick={() => performSharedAction('cancel', record.id)}>Cancel work</Button></div>}
                {record.actor_id === authorityActorId && record.state === 'reserved' && <>{record.definition?.execution_model === 'thermal_batch' ? <div className="iso-priority"><label>Temperature °C<input aria-label="Meal temperature" type="number" value={mealThermalRecord.temperature} onChange={(event) => setMealThermalRecord((current) => ({ ...current, temperature: event.target.value }))} /></label><label>Minutes<input aria-label="Meal heated minutes" type="number" value={mealThermalRecord.minutes} onChange={(event) => setMealThermalRecord((current) => ({ ...current, minutes: event.target.value }))} /></label></div> : record.definition?.execution_model === 'condition_restoration' ? <div className="iso-priority"><label>Condition before<input aria-label="Pump condition before repair" type="number" min="0" max="1" step="0.01" value={repairConditionRecord.before} onChange={(event) => setRepairConditionRecord((current) => ({ ...current, before: event.target.value }))} /></label><label>Observed after<input aria-label="Pump condition after repair" type="number" min="0" max="1" step="0.01" value={repairConditionRecord.after} onChange={(event) => setRepairConditionRecord((current) => ({ ...current, after: event.target.value }))} /></label></div> : record.definition?.execution_model === 'finite_site_extraction' ? <div className="iso-priority"><label>Site stock before<input aria-label="Resource stock before extraction" type="number" min="0" step="1" value={extractionObservation.stockBefore} onChange={(event) => setExtractionObservation((current) => ({ ...current, stockBefore: event.target.value }))} /></label><label>Observed yield<input aria-label="Observed extraction yield" type="number" min="0" step="1" value={extractionObservation.observedYield} onChange={(event) => setExtractionObservation((current) => ({ ...current, observedYield: event.target.value }))} /></label></div> : <input aria-label="Ordered calibration readings" value={calibrationReadings} onChange={(event) => setCalibrationReadings(event.target.value)} />}<div className="iso-priority"><Button variant="outline" onClick={() => executeSharedWork(record)}>Execute measured work</Button><Button variant="ghost" onClick={() => performSharedAction('cancel', record.id)}>Release reservation</Button></div></>}
                {record.actor_id !== authorityActorId && record.state === 'submitted' && <Button variant="outline" onClick={() => performSharedAction('verify', record.id)}>Independently verify</Button>}
                {record.verifier_id === authorityActorId && record.state === 'verified' && <Button variant="outline" onClick={() => performSharedAction('commission', record.id)}>Commission verified output</Button>}
              </>}
            </article>)}
            <small>CU shown here is internal, balanced, evidence-linked valuation. It is not spendable or redeemable.</small>
            <h2>Lever-pump research</h2>
            <p>Stand beside the measurement laboratory. Dimensions use meters; predicted delivery derives from lever ratio, piston area, stroke, and declared efficiency.</p>
            <article>
              <b>Communal water verification</b>
              <span>{serverSnapshot.state.resources.tested_water} tested units available · {activePlayer.inventory?.water || 0} raw units held</span>
              {(activePlayer.inventory?.water || 0) > 0 && <Button variant="outline" onClick={() => performAuthorityAction({ type: 'submit_water_batch', source_site: 'well-site', amount: Math.min(6, Math.floor(activePlayer.inventory.water)) })}>Deliver latest well collection for testing</Button>}
              <small>Raw water has no public value until Mira verifies its source custody and safety. Worn machinery can lower the measured result.</small>
            </article>
            {(serverSnapshot.state.water_system?.batches || []).slice().reverse().slice(0, 5).map((batch) => <article key={batch.id}>
              <b>{batch.id} · {batch.status.replaceAll('_', ' ')}</b>
              <span>{batch.amount} units from {batch.source_site} · submitted by {batch.submitted_by}</span>
              <small>{batch.tested_by ? `Mira measured safety ${batch.safety.toFixed(2)} · ${batch.accepted ? 'entered communal supply' : 'rejected'}` : `Test due tick ${batch.test_due_tick}`}</small>
            </article>)}
            {(serverSnapshot.state.water_system?.work_orders || []).slice().reverse().slice(0, 4).map((order) => <article key={order.id}>
              <b>{order.id} · {order.status.replaceAll('_', ' ')}</b>
              <span>{order.collector} collects from {order.source_site}; {order.tester} verifies · target {order.target_amount}</span>
              <small>{order.history.at(-1)?.reason || order.history.at(-1)?.cause || `Latest transition at tick ${order.history.at(-1)?.tick}`}{order.batch_id ? ` · ${order.batch_id}` : ''}</small>
            </article>)}
            <form onSubmit={proposePumpDesign}>
              <input value={pumpDesign.name} onChange={(event) => setPumpDesign((current) => ({ ...current, name: event.target.value }))} aria-label="Pump design name" maxLength={80} />
              <label>Effort arm (m)<input type="number" min="0.01" step="0.01" value={pumpDesign.effortArm} onChange={(event) => setPumpDesign((current) => ({ ...current, effortArm: event.target.value }))} /></label>
              <label>Load arm (m)<input type="number" min="0.01" step="0.01" value={pumpDesign.loadArm} onChange={(event) => setPumpDesign((current) => ({ ...current, loadArm: event.target.value }))} /></label>
              <label>Piston diameter (m)<input type="number" min="0.01" step="0.01" value={pumpDesign.pistonDiameter} onChange={(event) => setPumpDesign((current) => ({ ...current, pistonDiameter: event.target.value }))} /></label>
              <label>Stroke (m)<input type="number" min="0.01" step="0.01" value={pumpDesign.stroke} onChange={(event) => setPumpDesign((current) => ({ ...current, stroke: event.target.value }))} /></label>
              <label>Efficiency<input type="number" min="0.3" max="0.95" step="0.01" value={pumpDesign.efficiency} onChange={(event) => setPumpDesign((current) => ({ ...current, efficiency: event.target.value }))} /></label>
              <Button type="submit">Submit dimensioned design</Button>
            </form>
            {(serverSnapshot.state.research?.designs || []).slice().reverse().map((design) => <article key={design.id}>
              <b>{design.name}</b><span>{design.status.replace(/_/g, ' ')}</span>
              {design.prediction && <small>MA {design.prediction.mechanical_advantage} · predicted {design.prediction.predicted_liters_per_stroke} L/stroke</small>}
              {design.test_result && <small>Observed {design.test_result.observed_liters_per_stroke} L/stroke · error {(design.test_result.relative_error * 100).toFixed(1)}%</small>}
              {design.review?.reason && <small>{design.review.reason}</small>}
            </article>)}
          </details>}

          {localPracticeEnabled && !worldServerConfigured && <>
          <div className="iso-economy-panel">
            <p className="iso-kicker">SHADOW VIRTUCONOMY</p>
            <div className="iso-economy-mode"><span>Accounting mode</span><b>{simulation.economy?.mode || 'shadow'}</b></div>
            <p>Balances are non-transferable test records. Every credit has an equal treasury debit and linked evidence.</p>
            <div className="iso-priority">
              <span>Public contract priority</span>
              <div>
                {['food', 'water'].map((priority) => <Button key={priority} variant={simulation.economy?.productionPriority === priority ? 'default' : 'outline'} onClick={() => chooseProductionPriority(priority)}>{priority}</Button>)}
              </div>
            </div>
            <div className="iso-balances">
              {Object.entries(simulation.economy?.accounts || {}).map(([account, balance]) => <span key={account}>{account}<b>{balance.toFixed(2)} CU</b></span>)}
            </div>
            <div className="iso-market">
              {Object.entries(simulation.economy?.prices || {}).map(([commodity, price]) => <span key={commodity}>{commodity}<b>{price.toFixed(2)}</b></span>)}
            </div>
            <small>Total verified output value: {(simulation.economy?.totalOutputValue || 0).toFixed(2)} CU</small>
            {(simulation.economy?.journal || []).slice(0, 4).map((entry) => <article key={entry.id}><b>{entry.to}</b><span>+{entry.amount.toFixed(2)} · {entry.memo}</span><small>{entry.evidence}</small></article>)}
          </div>

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

          </>}
          <div className="iso-inspector">
            <p className="iso-kicker">INSPECTOR</p>
            {selectedView ? (
              <>
                <h3>{selectedView.name}</h3>
                <p>{selectedView.role || (selectedView.stage === 4 ? 'Commissioned structure' : 'Construction work order pending verification')}</p>
                {selectedView.needs && <p>Task: {selectedView.task?.label || 'Choosing an intention'}<br /><em>{selectedView.task?.reason || 'Evaluating available actions.'}</em><br />Nutrition {Math.round(selectedView.needs.nutrition)} · Hydration {Math.round(selectedView.needs.hydration)} · Rest {Math.round(selectedView.needs.rest)} · Belonging {Math.round(selectedView.needs.belonging)}</p>}
                {selectedView.survival_activity && <p>Survival action: {selectedView.survival_activity.kind} · {selectedView.survival_activity.status}{selectedView.survival_activity.blocked_by ? ` · waiting for ${selectedView.survival_activity.blocked_by}` : ''}</p>}
                {selectedView.schedule && <p>Schedule: {String(selectedView.schedule.shiftStart).padStart(2, '0')}:00–{String(selectedView.schedule.shiftEnd).padStart(2, '0')}:00<br />Inventory: {Object.entries(selectedView.inventory || {}).map(([item, amount]) => `${item} ${amount}`).join(', ') || 'empty'}</p>}
                {selectedView.memories?.length > 0 && <div className="iso-memories"><strong>Work memories</strong>{selectedView.memories.slice(0, 3).map((memory, index) => <small key={`${memory.tick}-${index}`}>{memory.text}</small>)}</div>}
                {selectedView.stage && selectedView.stage < 4 && <p>Progress requires an accepted work order, supplied materials, qualified labor time, and inspection evidence.</p>}
                {selectedResource && <>
                  {selectedTileResources.map((resource) => <p key={resource.id}>Type: {resource.type} · {resource.name} · Stock {typeof resource.stock === 'object' ? Object.entries(resource.stock).map(([item, amount]) => `${item} ${amount}`).join(', ') : `${Math.floor(resource.stock || 0)} / ${resource.capacity || '—'}`}</p>)}
                  {selectedResource.progress !== undefined && <p>Construction progress: {selectedResource.progress}/3</p>}
                  {selectedResource.installed_pump && <p>Installed technology: {selectedResource.installed_pump.design_id} · predicted {selectedResource.installed_pump.predicted_liters_per_stroke} L/stroke<br />Condition {Math.round(selectedResource.installed_pump.condition * 100)}% · {selectedResource.installed_pump.status} · {selectedResource.installed_pump.cycles} field cycles</p>}
                  {selectedMaintenanceOrder && <p><strong>Maintenance order {selectedMaintenanceOrder.id}</strong><br />{selectedMaintenanceOrder.assigned_to ? `Assigned to ${selectedMaintenanceOrder.assigned_to}` : 'Awaiting assignment'} · requires timber {selectedMaintenanceOrder.required_inputs.timber}, containers {selectedMaintenanceOrder.required_inputs.containers}, and {selectedMaintenanceOrder.required_tool}{selectedMaintenanceOrder.blockers?.at(-1)?.status === 'unresolved' ? <><br />Blocked by: {selectedMaintenanceOrder.blockers.at(-1).missing.join(', ')}</> : null}{selectedMaintenanceOrder.depletion_notices?.at(-1)?.status === 'unresolved' ? <><br />Expedition found no regional {selectedMaintenanceOrder.depletion_notices.at(-1).resource}; awaiting replenishment or another source.</> : null}{selectedMaintenanceOrder.procurement_history?.length ? <><br />Verified deliveries: {selectedMaintenanceOrder.procurement_history.map((entry) => `${entry.amount} ${entry.resource} from ${entry.source}`).join('; ')}</> : null}</p>}
                  {selectedResource.stage && <p>Growth stage: {selectedResource.stage}{selectedResource.readyTick ? ` · ready tick ${selectedResource.readyTick}` : ''}</p>}
                  {selectedResource.wellbeing !== undefined && <p>Animal wellbeing: {Math.round(selectedResource.wellbeing)} · fed through tick {selectedResource.fedUntilTick}</p>}
                  {selectedResourceOptions.map((option) => <Button key={option.key} variant="outline" onClick={() => interactWithResource(option)}>{option.label}</Button>)}
                  {actionReceipt && <p role="status" data-tone={actionReceipt.tone}>{actionReceipt.text}</p>}
                  <small>Stand on an adjacent tile. Tools, energy, stock, growth time, and animal care are enforced.</small>
                </>}
              </>
            ) : <p>Select a resident or structure in the settlement.</p>}
            <p>Energy {Math.round(activePlayer.energy ?? 100)} · Inventory {Object.entries(activePlayer.inventory || {}).filter(([, amount]) => amount > 0).map(([item, amount]) => `${item} ${Math.floor(amount * 100) / 100}`).join(', ') || 'empty'}</p>
          </div>

          {localPracticeEnabled && !worldServerConfigured && <><div className="iso-event-feed">
            <h3><Activity size={14} /> WORLD EVENTS</h3>
            {simulation.events.slice(0, 10).map((event, index) => (
              <article key={`${event.tick}-${event.actor}-${index}`}><b>{event.actor}</b><span>{event.text}</span><small>tick {event.tick} · {event.type.replace(/_/g, ' ')}</small></article>
            ))}
          </div>

          <div className="iso-evidence-feed">
            <h3>CAUSAL &amp; EVIDENCE RECORDS</h3>
            {simulation.evidenceRecords?.slice(0, 6).map((record) => <article key={record.id}><b>{record.change}</b><span>Actors: {record.actors.join(', ') || 'none'} · Tools: {record.tools.join(', ') || 'none'}</span><small>Inputs {JSON.stringify(record.inputs)} · Measurements {JSON.stringify(record.measurements)} · Inspector {record.inspector || 'pending'}</small></article>)}
          </div>

          <div className="iso-failure-feed">
            <h3>FAILURE &amp; RECOVERY</h3>
            {simulation.failures?.length ? simulation.failures.slice(0, 6).map((failure, index) => <article key={`${failure.tick}-${index}`} className={failure.recovered ? 'recovered' : ''}><b>{failure.actor} · {failure.action}</b><span>{failure.reason}</span><small>{failure.recovered ? `Recovered at tick ${failure.recoveredAtTick}` : 'Work remains stopped'}</small></article>) : <p>No unresolved work failures.</p>}
            <small>World saves use checksummed revisions and restore the last known-good backup after an interrupted write.</small>
          </div>

          <div className="iso-note">
            <strong>Desktop persistence</strong>
            <p>The desktop build stores checksummed revisions with a known-good backup. Server-authoritative work orders and CU escrow remain a later milestone.</p>
            {savedAt && <small>Saved {savedAt.toLocaleTimeString()}</small>}
          </div>
          </>}
          {isOwner && <JarvisPanel
            activity={buildMode ? 'Observing blueprint placement' : selectedView ? `Reviewing ${selectedView.name}` : 'Monitoring settlement activity'}
            directives={serverSnapshot?.state.institutions?.governance?.owner_directives || []}
            canPropose={Boolean(serverSnapshot)}
            onProposeDirective={proposeOwnerDirective}
          />}
          {isOwner && <details><summary>Operator diagnostics</summary><DesktopDiagnostics /><CausalLedgerPanel /></details>}
        </aside>
      </main>
    </div>
  );
};

export default IsometricSettlement;
