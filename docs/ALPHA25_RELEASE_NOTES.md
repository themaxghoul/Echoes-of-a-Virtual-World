# Alpha.25 owner-identity recovery

Alpha.25 corrects the legacy Luciferous desktop account discovered in the installed test profile: the account existed, but its permission level remained `basic` because no immutable `owner.json` binding had been created.

## Password-authenticated legacy enrollment

- A valid login to an existing reserved `Luciferous` account can create the missing one-time UUID owner binding when no separate bootstrap password is configured.
- The binding occurs only after the stored PBKDF2 password hash is successfully verified.
- A wrong password returns no account and writes no owner binding.
- New registration still cannot claim the reserved Luciferous name without private provisioning.
- After binding, authority follows the immutable UUID across restart and username changes.
- The public profile receives `is_owner: true`, private permission tier `sirix_1`, null-read inspection policy, and owner-only Jarvis storage access.

The persistent multiplayer service still requires its independently authenticated server-side Luciferous UUID in `EOV_OWNER_USER_ID`. Desktop ownership never authorizes a network identity merely because the two accounts share a name.

Alpha.25 retains schema 17 and all Alpha.24 simulation systems.
