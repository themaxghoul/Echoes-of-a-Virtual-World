# Alpha 36 self-hosted playtest services

The public playtest is a Windows desktop client plus source for two local services. It does **not** include hosted multiplayer, pre-created accounts, secrets, or a world database.

## Requirements

- Windows 10/11 x64 for the desktop client.
- Python 3.12 and Docker Desktop for the self-hosted services.
- A private test network. Do not expose these development services to the public internet without a separate security review and deployment hardening.

## Start the services

1. Extract the server ZIP. Copy `backend/.env.playtest.example` to `backend/.env`; create a unique random `EOV_SESSION_SECRET` of at least 32 bytes and use the same value for both services. Keep this file private.
2. From the extracted folder, start MongoDB with `docker compose up -d mongo`.
3. In PowerShell, install dependencies and start the authentication API:

   ```powershell
   Set-Location .\backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r .\playtest-requirements.txt
   .\run_auth_server.ps1
   ```

4. Open a second PowerShell window in the same `backend` folder, activate `.venv`, then start the world service:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   .\run_persistent_server.ps1
   ```

5. In the client settings, set Authentication API to `http://127.0.0.1:8000` and World Server to `http://127.0.0.1:8765`, then create a new test account. Login secrets and accounts are not included in the download.

The MongoDB compose file binds to loopback and stores data in a named Docker volume. World state is stored in `backend/data/persistent-world.sqlite3`. Stop the services with Ctrl+C; the world clock performs bounded catch-up when reopened.

The integrated AI model provider, first-person view, combat, crafting, and paid economy are not part of this playtest. Provisional CU is not spendable or redeemable. Never reuse a personal login password for the signing secret.
