const INTERACTIVE_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON']);

function shouldToggleChat(event) {
  if (String(event?.key || '').toLowerCase() !== 't') return false;
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return false;
  const target = event.target;
  if (INTERACTIVE_TAGS.has(String(target?.tagName || '').toUpperCase())) return false;
  return target?.isContentEditable !== true;
}

module.exports = { shouldToggleChat };
