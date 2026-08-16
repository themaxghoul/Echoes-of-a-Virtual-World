# Alpha.14 identity and authorization boundary

Alpha.14 treats identity as a server-established fact. A successful login or registration returns a signed, 15-minute bearer session. Protected HTTP requests derive the actor from that session; a user or character identifier supplied by a client is never sufficient authority.

## Enforced now

- HMAC-SHA256 session tokens have issuer, audience, subject, session, version, issued-at, not-before, and expiry claims.
- Sessions are recorded server-side and can be revoked at logout. Disabled accounts and token-version changes invalidate existing sessions.
- User and character reads enforce self, owner, or administrator access from database-backed roles.
- Character creation and login tracking reject client identity mismatches.
- Legacy chat WebSockets require a one-use, 60-second ticket bound to the authenticated user and location. Display identity is server-derived.
- Persistent-world mutations take their actor only from the signed session subject.
- Credentialed CORS is restricted to explicitly configured origins; wildcard credential origins are rejected.
- New account passwords require at least 12 characters.
- The private owner is bound to an immutable account UUID. Owner-only Jarvis and creator/administrator capabilities require the persisted UUID, owner flag, and private owner role to agree; a username alone is never authority.

## Deliberately quarantined

All legacy mutations except logout, WebSocket-ticket creation, login tracking, and character creation return `LEGACY_MUTATION_QUARANTINED`. This includes trading, inventories, guilds, jobs and rewards, earnings and withdrawals, marketplace submission, and administrative/world-changing operations. Each route must be audited and converted to server-derived ownership and capability checks before it can be re-enabled.

This quarantine is an intentional compatibility break. It prevents the alpha from presenting unaudited operations as secure.

## Deployment requirements

- Set `EOV_SESSION_SECRET` to a cryptographically random secret of at least 32 bytes on both the authentication API and persistent-world server. Never commit it.
- Set `CORS_ORIGINS` and `EOV_ALLOWED_ORIGINS` to exact trusted origins.
- Set `EOV_OWNER_PASSWORD` privately only for initial owner provisioning. Optionally set `EOV_OWNER_USER_ID` to bind an existing account before the first binding is stored. Never ship either value in source or a packaged executable.
- Terminate production traffic with HTTPS/WSS.
- Do not enable real-money deposits, withdrawals, or spendable CU in this alpha.
- Add rate limiting, account recovery, MFA for privileged accounts, key rotation, CSRF review if cookies are introduced, security logging, and an independent penetration test before public or financial release.

The persistent-world service validates signature and expiry but does not yet perform immediate session-revocation introspection. The 15-minute token lifetime bounds that exposure; introspection or short-lived access/refresh token rotation remains a pre-public-release requirement.
