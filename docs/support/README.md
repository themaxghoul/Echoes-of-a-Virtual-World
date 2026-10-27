# Public Support and Playtest Page

The page in `docs/support/index.html` is served through GitHub Pages from the repository's `docs/` folder. Its release panel queries the public GitHub Releases API and only enables the desktop/server downloads after both matching assets exist; no downloadable binary is stored in the repository.

## Enable publishing

In the repository's **Settings → Pages**, set the build and deployment source to **GitHub Actions**. The workflow `.github/workflows/deploy-support-pages.yml` then deploys this page from `main` and the current playtest branch. The expected URL is `https://themaxghoul.github.io/Echoes-of-a-Virtual-World/support/`.

The page is informational and community-supported. It deliberately has no payment form: the GitHub Sponsors profile/payout destination is not active in this project setup, and CU remains non-spendable accounting. Do not add an external checkout until the owner has a verified payout destination and has reviewed the legal, tax, privacy, and fraud controls.

## Release coupling

The matching page download appears only after the release workflow publishes both:

- `EoV-Alpha36-Windows-x64.zip`
- `EoV-Alpha36-Persistent-Server.zip`

The page resolves actual asset URLs from GitHub's latest-release API response instead of guessing file locations. If a release is missing or incomplete, it directs visitors to the release list rather than a dead file link.

The page says playtesters must provide authentication and world services. It does not claim that the project operates a managed public multiplayer host.
