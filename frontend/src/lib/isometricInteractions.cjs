function operationForSite(site, inventory = {}, tick = 0) {
  if (site.type === 'store') return { operation: 'checkout' };
  if (site.type === 'tree') return { operation: 'chop' };
  if (site.type === 'mineral') return { operation: 'mine' };
  if (site.type === 'reeds') return { operation: 'harvest' };
  if (site.type === 'well') {
    if (site.progress < 3) return { operation: 'dig' };
    if (site.installed_pump?.maintenance_due) {
      return inventory.wrench > 0 && inventory.timber > 0 && inventory.containers > 0
        ? { operation: 'maintain_pump' }
        : { operation: 'inspect_pump' };
    }
    return { operation: 'draw_water' };
  }
  if (site.type === 'farm') return { operation: site.stage === 'untilled' ? 'till' : site.stage === 'tilled' ? 'sow' : 'harvest' };
  if (site.type === 'cattle') return { operation: inventory.feed > 0 && site.fedUntilTick < tick ? 'feed' : 'milk' };
  return { operation: 'inspect' };
}

function resourceInteractionOptions(resources, tile, inventory = {}, tick = 0) {
  if (!tile) return [];
  return resources
    .filter((site) => site.x === tile.x && site.y === tile.y)
    .flatMap((site) => {
      if (site.type === 'store') {
        return Object.entries(site.stock || {})
          .filter(([item, stock]) => stock >= (item === 'seed' || item === 'feed' ? 4 : 1))
          .map(([item]) => ({
            key: `${site.id}:checkout:${item}`,
            siteId: site.id,
            siteName: site.name,
            operation: 'checkout',
            item,
            quantity: item === 'seed' || item === 'feed' ? 4 : 1,
            label: `checkout ${item} · ${site.name}`,
          }));
      }
      const action = operationForSite(site, inventory, tick);
      return [{
        key: `${site.id}:${action.operation}`,
        siteId: site.id,
        siteName: site.name,
        ...action,
        label: `${action.operation.replaceAll('_', ' ')} · ${site.name}`,
      }];
    });
}

function checkoutLocalStoreItem(site, inventory, item, quantity = 1) {
  if (!site?.stock || !item || quantity < 1 || site.stock[item] < quantity) {
    return { accepted: false, reason: 'the requested store item is unavailable' };
  }
  site.stock[item] -= quantity;
  inventory[item] = (inventory[item] || 0) + quantity;
  return { accepted: true, outputs: { [item]: quantity } };
}

function approachTileForSite(site, player, observedTiles = null, size = 64) {
  if (!site || !player) return null;
  const distance = Math.abs(site.x - player.x) + Math.abs(site.y - player.y);
  if (distance <= 1) return { x: player.x, y: player.y };
  const candidates = [
    { x: site.x - 1, y: site.y },
    { x: site.x + 1, y: site.y },
    { x: site.x, y: site.y - 1 },
    { x: site.x, y: site.y + 1 },
  ].filter((tile) => {
    if (tile.x < 0 || tile.y < 0 || tile.x >= size || tile.y >= size) return false;
    if (!observedTiles) return true;
    const observed = observedTiles[`${tile.x},${tile.y}`];
    return observed && observed.passable !== false;
  });
  candidates.sort((left, right) => {
    const leftDistance = Math.abs(left.x - player.x) + Math.abs(left.y - player.y);
    const rightDistance = Math.abs(right.x - player.x) + Math.abs(right.y - player.y);
    return leftDistance - rightDistance
      || Math.abs(left.y - player.y) - Math.abs(right.y - player.y)
      || left.x - right.x
      || left.y - right.y;
  });
  return candidates[0] || null;
}

function formatResourceReceipt(result, siteName = 'Resource site') {
  if (!result?.accepted) {
    return { tone: 'blocked', text: `${siteName} · blocked · ${result?.reason || 'the action was not accepted'}` };
  }
  const gains = Object.entries(result.outputs || {})
    .filter(([, amount]) => typeof amount === 'number' && amount !== 0)
    .map(([item, amount]) => `${item.replaceAll('_', ' ')} ${amount > 0 ? '+' : ''}${amount}`);
  const details = [
    `${siteName} · ${String(result.operation || 'interaction').replaceAll('_', ' ')} complete`,
    ...gains,
    Number.isFinite(result.energy) ? `energy ${result.energy}` : null,
    'output held in your inventory',
  ].filter(Boolean);
  return { tone: 'success', text: details.join(' · ') };
}

function fallbackNpcReply(npc, content) {
  const words = String(content || '').toLowerCase();
  if (/teach|learn|lesson|show you|explain|algorithm/.test(words)) {
    return 'I can listen to the idea. I will treat it as a proposal until observation, practice, and reproducible evidence demonstrate that it works.';
  }
  if (/tree|wood|stone|mine|resource/.test(words)) {
    return 'Use what you can verify: trees need an axe, seams need a pick, and every removal changes what remains.';
  }
  if (/hello|\bhi\b|\bhey\b|talk|socialize|conversation|friend|feeling|share an idea/.test(words)) {
    return `I’m ${npc.name}. I can make room to listen and talk; tell me what matters to you, and I will decide what I think of it.`;
  }
  if (/why|what|where|when|how|can you|\?/.test(words)) {
    return `From what I can currently perceive, I am considering ${npc.task?.label?.toLowerCase() || 'what to do next'}. I can still discuss your question separately.`;
  }
  return 'I heard you. I can keep this conversation separate from my work plan; tell me more about what you mean.';
}

module.exports = {
  approachTileForSite,
  checkoutLocalStoreItem,
  fallbackNpcReply,
  formatResourceReceipt,
  operationForSite,
  resourceInteractionOptions,
};
