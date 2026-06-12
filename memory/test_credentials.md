# Test Credentials

## Sirix-1 Supreme Admin
- Username: `sirix_1`
- User ID: `sirix_1_supreme`
- Password: `HCLynnTV04` (also in backend/.env as SIRIX_ADMIN_PASSWORD)
- Login: POST /api/auth/login {"username":"sirix_1","password":"HCLynnTV04"}

## Frontend session (localStorage-based auth)
Set before navigating to authed pages:
- localStorage.setItem('userId','sirix_1_supreme')
- localStorage.setItem('username','sirix_1')

## State of sirix_1_supreme (June 12, 2026)
- ~4000+ VE$ in entity_wallets (balance_ve)
- Owns: frame_neon (equipped), color_neon_pink (equipped chat_color), palette_neon, title_pioneer, title_forgemaster
- Has saved pixel avatar; was featured in Hall of Echoes spotlight
- Active Forge Surge boost may have expired (24h from June 12 23:29 UTC)

## Data API
- Demo analytics key: `demo_analytics_key` (GET /api/data-api/analytics/summary?api_key=...)
