export function snapshotFresh(lastSnapshot, now) {
  return lastSnapshot > 0 && now - lastSnapshot <= 5000;
}
