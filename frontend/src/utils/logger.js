/**
 * Logger utility for production-safe logging
 * In production, these can be replaced with proper logging service (Sentry, LogRocket)
 */

const isDevelopment = process.env.NODE_ENV === 'development';

const logger = {
  log: (...args) => {
    if (isDevelopment) {
      console.log('[DEV]', ...args);
    }
    // In production, send to logging service
  },
  
  warn: (...args) => {
    if (isDevelopment) {
      console.warn('[DEV WARN]', ...args);
    }
    // In production, send to logging service
  },
  
  error: (...args) => {
    // Always log errors, but sanitize in production
    if (isDevelopment) {
      console.error('[ERROR]', ...args);
    } else {
      // In production, send to error tracking service (Sentry, etc.)
      // Avoid logging sensitive data
      const sanitizedArgs = args.map(arg => {
        if (typeof arg === 'object' && arg !== null) {
          // Remove sensitive fields
          const { password, token, apiKey, ...safe } = arg;
          return safe;
        }
        return arg;
      });
      console.error('[ERROR]', ...sanitizedArgs);
    }
  },
  
  debug: (...args) => {
    if (isDevelopment) {
      console.debug('[DEBUG]', ...args);
    }
  }
};

export default logger;
