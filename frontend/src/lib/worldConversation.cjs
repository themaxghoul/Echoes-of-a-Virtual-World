function nearbyResidents(snapshot, radius = 4) {
  const actor = snapshot?.state?.players?.[snapshot.viewer_id];
  if (!Array.isArray(actor?.location)) return [];
  const distance = (resident) => Math.abs(resident.location[0] - actor.location[0]) + Math.abs(resident.location[1] - actor.location[1]);
  return Object.values(snapshot.state.npcs || {})
    .filter(resident => Array.isArray(resident.location)
      && (resident.current_region || 'settlement') === (actor.current_region || 'settlement')
      && distance(resident) <= radius)
    .sort((a, b) => distance(a) - distance(b) || a.id.localeCompare(b.id));
}
function speechAction(snapshot, content, recipientId = '') {
  if (!content.trim()) throw new Error('Enter a message first.');
  const residents = nearbyResidents(snapshot);
  if (recipientId && !residents.some(resident => resident.id === recipientId)) {
    throw new Error('That resident is no longer within hearing. Choose someone nearby.');
  }
  if (!residents.length) throw new Error('Nobody is close enough to hear you. Move nearer to a resident.');
  return { type: 'speak', content: content.trim(), target_id: recipientId || residents[0].id };
}
function mergeMessages(current, incoming) {
  const merged = new Map(current.map(message => [message.id, message]));
  for (const message of incoming) if (message.id) merged.set(message.id, message);
  return [...merged.values()].slice(-150);
}
module.exports = { nearbyResidents, speechAction, mergeMessages };
