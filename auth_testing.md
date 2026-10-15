# Existing cookie-auth verification for the live editor

Preserve current JWT httpOnly cookies, CSRF double-submit protection and roles.
No new login method, seed account or credential change is part of this task.

1. Verify seeded owner and bcrypt hash/indexes using existing environment credentials.
2. Log in via `/api/auth/login`; verify authenticated `/api/auth/me` with cookie jar.
3. Verify launcher on all public routes without `?edit` and with legacy setting disabled.
4. Close panel, navigate and reload: launcher remains, panel can reopen.
5. Logout succeeds server-side before local auth clears. Launcher/panels disappear in
   the current tab and another open tab. Stale edit session flag grants no access.
6. Expired access token may use the existing refresh endpoint; invalid refresh ends
   the UI session. Network errors must not falsely claim a successful logout.
7. Anonymous writes and non-publisher writes remain rejected; config-only global
   changes remain config-only. Mutations carry the CSRF header.
8. Repeat using the compiled production assets and REAL APIs, not mocked responses.
   UI asset interception under the preview origin may serve build files for testing;
   do not intercept API responses or run a second backend.