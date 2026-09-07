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

module.exports = { checkoutLocalStoreItem, fallbackNpcReply, operationForSite, resourceInteractionOptions };
