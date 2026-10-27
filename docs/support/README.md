# Public Support and Playtest Page

The page in `docs/support/index.html` is served through the repository's existing GitHub Pages workflow at `/support/`. The same deployment preserves the existing browser alpha at the site root. Its release panel queries the public GitHub Releases API and only enables the desktop/server downloads after both matching assets exist; no downloadable binary is stored in the repository.

## Enable publishing

In the repository's **Settings → Pages**, set the build and deployment source to **GitHub Actions**. The workflow `.github/workflows/pages.yml` deploys `docs/play/` at the site root and `docs/support/` at `/support/` from the protected `main` branch. The expected support URL is `https://themaxghoul.github.io/Echoes-of-a-Virtual-World/support/`; the existing browser alpha remains at `https://themaxghoul.github.io/Echoes-of-a-Virtual-World/`.

The page is informational and community-supported. It deliberately has no payment form: the GitHub Sponsors profile/payout destination is not active in this project setup, and CU remains non-spendable accounting. Do not add an external checkout until the owner has a verified payout destination and has reviewed the legal, tax, privacy, and fraud controls.

## Release coupling

The matching page download appears only after the release workflow publishes both:

- `EoV-Alpha36-Windows-x64.zip`
- `EoV-Alpha36-Persistent-Server.zip`

The page resolves actual asset URLs from GitHub's latest-release API response instead of guessing file locations. If a release is missing or incomplete, it directs visitors to the release list rather than a dead file link. The browser alpha is a separate build/runtime and does not share accounts, saves, or world state with the Alpha 36 desktop/server package.

The page says playtesters must provide authentication and world services. It does not claim that the project operates a managed public multiplayer host.
