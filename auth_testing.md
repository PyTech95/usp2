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

## Content promotion / republish password preservation (2026-10-15)
- Explicit requirement supersedes the generic playbook's env-password rotation example:
  startup creates the initial owner ONLY when no user exists. Existing hashes, roles,
  profiles and sessions must stay byte-for-byte unchanged even if ADMIN_PASSWORD or
  ADMIN_EMAIL differs from a deployed user's current account.
- Test create-only initialization in an isolated database and run startup/seed twice.
- Empty notes/register collections on an existing site must not resurrect seed samples.
- Content release importer must never touch users, enquiries, register, login_attempts
  or tokens. Test backup-first import, idempotence and failure rollback separately.