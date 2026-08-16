# EoV 0.3.0-alpha.1 — Desktop Foundation

This milestone packages Echoes of Virtuality as a portable Windows x64 application and moves the isometric world and Jarvis memory behind a recoverable desktop persistence boundary.

## Running the test build

1. Extract the entire portable ZIP.
2. Run `EchoesOfVirtuality.exe` from the extracted folder.
3. Keep the other packaged files beside the executable.

The build is unsigned, so Windows may identify the publisher as unknown. Do not bypass a security warning unless the file hash matches the release notes and you trust the source of the archive.

## Reliability included

- Local packaged application code; no remote editor or analytics scripts.
- Electron renderer sandbox, context isolation, and disabled Node integration.
- Narrow IPC methods for account-scoped world state, owner-only Jarvis memory, version, and diagnostics. Renderer-supplied storage identities are discarded in favor of the signed active desktop session.
- Checksummed save envelopes with schema version, revision, and timestamp.
- Atomic temporary-file writes and a known-good backup.
- Recovery tests for a deliberately corrupted live save.
- Desktop diagnostics showing application and save revisions.
- Browser fallback retained for development.

## Verification

- Desktop persistence tests: 3 passed.
- React production bundle: compiled successfully with pre-existing hook dependency warnings in legacy screens.
- Windows x64 package: produced successfully.
- Computer-driven smoke test: executable launched, rendered the landing screen, and navigated to authentication.
- Authentication was not automated or tested with stored credentials.

## Known boundaries

- This is a portable build, not an installed or code-signed release.
- The older prototype screens retain browser-local state until migrated deliberately.
- Jarvis model responses and encrypted server memory remain future work. Its desktop memory is owner-session scoped, and its persistent-world directives are owner-UUID authorized, replayable proposals rather than direct world edits.
- CU and work-order accounting are not server-authoritative.
- Save export/import and SQLite migration remain planned rather than claimed as complete.
