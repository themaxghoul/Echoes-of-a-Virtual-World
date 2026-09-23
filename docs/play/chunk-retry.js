/** Missing terrain must not turn each world snapshot into another failed request. */
export class ChunkRetry {
  constructor() {
    this.failures = new Map();
  }
  ready(key, now = Date.now()) {
    return (this.failures.get(key)?.until || 0) <= now;
  }
  succeeded(key) {
    this.failures.delete(key);
  }
  failed(key, error, now = Date.now()) {
    const attempts = (this.failures.get(key)?.attempts || 0) + 1;
    const delay = Math.min(300000, 8000 * 2 ** Math.min(attempts - 1, 6));
    this.failures.set(key, {
      attempts,
      until: Math.max(now + delay, Number(error.retryAt) || 0),
    });
    if (this.failures.size > 256)
      this.failures.delete(this.failures.keys().next().value);
  }
}
