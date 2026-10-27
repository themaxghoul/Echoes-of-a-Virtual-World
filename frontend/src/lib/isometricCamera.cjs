const TILE_W = 64;
const TILE_H = 32;
function clampZoom(value) {
  return Number.isFinite(value) ? Math.min(1.75, Math.max(0.5, value)) : 1;
}
function createCamera(width, height, player, zoom = 1) {
  return { width, height, x: player.x, y: player.y, zoom: clampZoom(zoom) };
}
function projectPoint(camera, x, y) {
  return {
    x: camera.width / 2 + ((x - camera.x) - (y - camera.y)) * TILE_W / 2 * camera.zoom,
    y: camera.height / 2 + ((x - camera.x) + (y - camera.y)) * TILE_H / 2 * camera.zoom,
  };
}
function tileAtPoint(camera, x, y) {
  const tx = (x - camera.width / 2) / (TILE_W / 2 * camera.zoom);
  const ty = (y - camera.height / 2) / (TILE_H / 2 * camera.zoom);
  return { x: Math.round(camera.x + (tx + ty) / 2), y: Math.round(camera.y + (ty - tx) / 2) };
}
function visibleBounds(camera, size) {
  const corners = [[0, 0], [camera.width, 0], [0, camera.height], [camera.width, camera.height]]
    .map(([x, y]) => tileAtPoint(camera, x, y));
  return {
    minX: Math.max(0, Math.min(...corners.map(p => p.x)) - 3),
    maxX: Math.min(size - 1, Math.max(...corners.map(p => p.x)) + 3),
    minY: Math.max(0, Math.min(...corners.map(p => p.y)) - 3),
    maxY: Math.min(size - 1, Math.max(...corners.map(p => p.y)) + 3),
  };
}
module.exports = { TILE_W, TILE_H, clampZoom, createCamera, projectPoint, tileAtPoint, visibleBounds };
