function serverAddress(saved, fallback = '') {
  return (saved?.trim() || fallback?.trim() || '').replace(/\/+$/, '');
}
module.exports = { serverAddress };
