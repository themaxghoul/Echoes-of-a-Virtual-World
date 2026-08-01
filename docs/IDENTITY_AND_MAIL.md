# Identity and in-world mail direction

## Identity boundaries

Production must keep these records separate:

- **Account:** one human or autonomous entity's unique authentication identity.
- **Profile:** public display name, accessibility preferences, locale, and communication preferences.
- **Character:** an in-world identity such as `sirix_1`; characters are assigned to accounts rather than used as passwords or authentication authorities.
- **Role grant:** owner, administrator, moderator, player, or AI capabilities with issuer, scope, reason, issue time, and revocation time.

No two people should share the owner account. Test bootstrap credentials must be removed before public launch. Production passwords should use Argon2id with a unique salt, while the owner account should require a passkey or MFA and maintain recovery codes and session-revocation controls.

## Login progression

1. Alpha: offline owner bootstrap plus existing username/password API.
2. Identity foundation: unique email and username identifiers, email verification, password reset, secure sessions, rate limiting, and audit records.
3. Federation: link social providers to an existing account; never derive roles from a provider profile.
4. Owner hardening: passkey/MFA requirement, step-up confirmation for privileged actions, and recovery workflow.

## In-world mailbox

The EoV mailbox is an internal messaging system first. Each account receives an address in an EoV-managed namespace, while messages use immutable IDs, sender/recipient account IDs, delivery state, timestamps, folders, abuse signals, and attachment metadata.

External email and custom domains belong behind provider adapters:

- inbound adapter validates SPF, DKIM, and DMARC results before delivery;
- outbound adapter signs mail and enforces rate, reputation, and abuse controls;
- custom domains require DNS ownership verification;
- provider addresses remain aliases and never become authorization evidence;
- attachments require size limits, type validation, malware scanning, and quarantine;
- users need block, report, mute, archive, export, and deletion controls;
- minors and public launch require a separate safety and retention review.

The internal mailbox can ship before external delivery. External SMTP should not be exposed directly from the game client.
