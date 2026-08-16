function projectObservedFrontier(snapshot, actorId) {
  const state = snapshot?.state;
  if (!state?.frontier || !state?.observed_tiles) {
    return { connected: false, size: 64, revision: null, tiles: {}, actors: [], route: null };
  }
  const tiles = {};
  for (const [key, source] of Object.entries(state.observed_tiles)) {
    tiles[key] = {
      key,
      position: Array.isArray(source.position) ? source.position.slice(0, 2) : key.split(',').map(Number),
      terrain: source.terrain || 'unknown',
      elevation: Number(source.elevation || 0),
      passable: source.passable !== false,
      visibility: source.visibility || 'surface',
      travelCostMilli: Number(source.travel_cost_milli || 1000),
      surface: source.surface ? { kind: source.surface.kind, material: source.surface.material, stock: Number(source.surface.stock || 0) } : null,
      excavationDepthCm: Number(source.excavation_depth_cm || 0),
      preparedFoundation: source.prepared_foundation === true,
    };
  }
  const allActors = [...Object.values(state.npcs || {}), ...Object.values(state.players || {})];
  const actors = allActors.filter((actor) => Array.isArray(actor.location)).map((actor) => ({ id: actor.id, name: actor.name || actor.username || actor.id, location: actor.location.slice(0, 2), kind: state.players?.[actor.id] ? 'human' : 'ai' }));
  const actor = state.players?.[actorId] || state.npcs?.[actorId];
  const sourceRoute = actor?.route;
  const route = sourceRoute && Array.isArray(sourceRoute.path) ? {
    status: sourceRoute.status,
    path: sourceRoute.path.map((point) => point.slice(0, 2)),
    index: Number(sourceRoute.index || 0),
    remaining: sourceRoute.path.slice(Number(sourceRoute.index || 0) + 1).map((point) => point.slice(0, 2)),
  } : null;
  return { connected: true, size: Number(state.frontier.size || 64), revision: snapshot.revision, tiles, actors, route };
}

module.exports = { projectObservedFrontier };
