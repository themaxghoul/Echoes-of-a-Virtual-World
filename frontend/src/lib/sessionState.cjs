/**
 * Persist the local profile and the separately authenticated network session.
 * A desktop token is only for local saves; world/multiplayer requests must use
 * the authentication service token and its server-derived subject.
 */
function applyAuthenticatedIdentity({ localStorage, sessionStorage, user, character, desktopToken, networkToken, networkUserId }) {
  if (!localStorage || !sessionStorage || !user?.id) throw new Error('Authenticated user is required');

  if (desktopToken) sessionStorage.setItem('eovDesktopAccessToken', desktopToken);
  // A missing network token during resume must not destroy an existing,
  // still-valid network session. Explicitly supplied values replace it.
  if (networkToken) sessionStorage.setItem('eovAccessToken', networkToken);
  if (networkUserId) localStorage.setItem('eovNetworkUserId', networkUserId);

  localStorage.setItem('userId', user.id);
  localStorage.setItem('username', user.username || '');
  localStorage.setItem('displayName', user.display_name || user.username || '');
  localStorage.setItem('isTranscendent', user.is_transcendent ? 'true' : 'false');
  localStorage.setItem('isOwner', user.is_owner ? 'true' : 'false');
  localStorage.setItem('permissionLevel', user.permission_level || 'basic');
  if (user.mailbox_address) localStorage.setItem('mailboxAddress', user.mailbox_address);
  if (character?.id) localStorage.setItem('currentCharacterId', character.id);
  if (character?.name) localStorage.setItem('characterName', character.name);
}

module.exports = { applyAuthenticatedIdentity };
