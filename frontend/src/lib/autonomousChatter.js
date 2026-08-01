const CHATTER_KEY = 'eov-autonomous-chatter-v1';

const VOICES = {
  'Elder Morvain': ['The south road needs another watch before dusk.', 'A promise is only useful when someone remembers it.', 'Put that concern in the public record.'],
  'Lyra the Wanderer': ['I heard the bridge crew changed its route again.', 'There is weather beyond the ridge.', 'Someone left fresh tracks near the eastern path.'],
  'Kael Ironbrand': ['Do not call it finished until the joint holds.', 'The stock count and the ledger disagree.', 'Precision saves material later.'],
  'Archivist Nyx': ['One witness is testimony; two independent records are evidence.', 'The earlier account contradicts this margin note.', 'Preserve the failed result as carefully as the successful one.'],
  'Innkeeper Mara': ['Rumor travels faster when supper is late.', 'They agreed on the price, but not the delivery.', 'Someone should ask before that story becomes accepted fact.'],
  'The Grove Keeper': ['Those branches were cut, not broken by wind.', 'Leave the soil as you found it.', 'Something moved through here before sunrise.'],
  'Sentinel Vex': ['Movement on the road. No threat confirmed.', 'Write the time beside the observation.', 'A warning is not a conviction.'],
  'Oracle Veythra': ['A prediction without a test is only a preference.', 'The instrument drifted after the temperature changed.', 'Ask what result would prove you wrong.'],
  'The Hooded Stranger': ['Not every silence is empty.', 'Maps end before the land does.', 'A name can move a crowd without moving a stone.'],
};

export function loadChatter() {
  try { const value = JSON.parse(localStorage.getItem(CHATTER_KEY)); return Array.isArray(value) ? value : []; } catch { return []; }
}

export function createChatterEvent(locations) {
  const occupied = locations.filter((location) => location.npcs?.length);
  if (!occupied.length) return null;
  const location = occupied[Math.floor(Math.random() * occupied.length)];
  const speaker = location.npcs[Math.floor(Math.random() * location.npcs.length)];
  const lines = VOICES[speaker] || ['The conversation continues without waiting for an audience.'];
  const event = { id: crypto.randomUUID(), speaker, content: lines[Math.floor(Math.random() * lines.length)], locationId: location.id, locationName: location.name, timestamp: Date.now(), kind: 'autonomous_speech' };
  const history = [...loadChatter(), event].slice(-250);
  localStorage.setItem(CHATTER_KEY, JSON.stringify(history));
  return event;
}
