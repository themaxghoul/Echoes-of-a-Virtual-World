function sampleMotion(motion, now, duration) {
  const progress = Math.max(0, Math.min(1, (now - motion.startedAt) / duration));
  const eased = progress * progress * (3 - (2 * progress));
  return {
    x: motion.from.x + (motion.to.x - motion.from.x) * eased,
    y: motion.from.y + (motion.to.y - motion.from.y) * eased,
  };
}

function stepEntityMotion(previous, target, now, duration = 500) {
  const destination = { x: Number(target.x), y: Number(target.y) };
  if (!Number.isFinite(destination.x) || !Number.isFinite(destination.y)) {
    throw new TypeError('entity target must have finite x/y coordinates');
  }

  if (!previous) {
    const motion = { from: destination, to: destination, startedAt: now };
    return { motion, position: destination };
  }

  const targetChanged = previous.to.x !== destination.x || previous.to.y !== destination.y;
  const motion = targetChanged
    ? { from: sampleMotion(previous, now, duration), to: destination, startedAt: now }
    : previous;
  return { motion, position: sampleMotion(motion, now, duration) };
}

module.exports = { stepEntityMotion };
