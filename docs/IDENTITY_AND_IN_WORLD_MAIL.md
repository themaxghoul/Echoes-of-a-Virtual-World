# Identity and in-world mail

## Separate identities

EoV distinguishes three concepts:

- **Authentication email**: optional private contact/login identifier on `user_profiles.email`. It is unverified until an external verification adapter confirms it.
- **Internal mailbox**: deterministic `username@eov.local` address created with an account. It works only inside EoV and is not an internet domain or deliverability claim.
- **Custom domain**: a normalized public DNS name claimed by an authenticated user. A claim begins as `pending_dns_verification` and cannot send or receive externally.

Registration validates a normalized 3-32 character username, 1-64 character display name, optional email syntax, and a password of at least 12 characters. Unique database indexes resolve concurrent username, email, and mailbox races. The server checks session-signing readiness before inserting an account and removes the narrowly scoped new record if session creation fails.

## In-world messages

Authenticated sessions derive the sender. Clients cannot supply a sender identity. A message targets an active internal mailbox, is rate-limited to ten messages per minute per sender, caps subject/body sizes, and carries a sender-scoped idempotency key. Exact retries return the prior message; conflicting reuse fails.

The throttle uses an atomic Mongo conditional update with a unique opaque bucket key, rather than a count-then-write check. Authentication, registration, WebSocket tickets, and domain claims use the same primitive with operation-specific windows. TTL indexes remove expired buckets without retaining raw addresses or usernames in the limiter key.

Mailbox reads derive the recipient from the session and never accept a user ID. External SMTP delivery is disabled.

## Custom-domain lifecycle

`POST /api/mail/domains/claim` returns a one-time DNS TXT value and stores only its hash. The domain remains non-operational. A future DNS adapter must independently resolve the TXT record, enforce retry limits and expiry, and record verification evidence. A separate provider adapter must then prove inbound/outbound routing. Domain text entered by a user is never itself proof of ownership.

## Desktop mode

The portable desktop app can register offline accounts without a browser backend. Passwords use PBKDF2-SHA256 with a unique random salt and 210,000 iterations; plaintext is never stored. Account writes are flushed to a temporary file and preserve a known-good backup. Offline profiles receive an internal mailbox identity, but cross-device mail and authoritative multiplayer sessions require the server path.
