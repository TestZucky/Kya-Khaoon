# Security

Kya Khaoon holds two things that matter: a user's Swiggy OAuth tokens, and a
small profile that includes allergies. This document says how to report a problem
with either, and what we already know about our own limits.

## Reporting a vulnerability

Email **rajawapp@gmail.com** with the subject `SECURITY`. Please include what you
found, how to reproduce it, and what an attacker could do with it.

You'll get an acknowledgement within **72 hours** and a fix or an explanation
within **14 days** for anything that exposes user data or allows acting as
another user.

Please don't open a public issue for a security problem, and please don't test
against real users' accounts — ask us for a test account instead.

We'll credit you when the fix ships, unless you'd rather stay anonymous.

### Good-faith research

We won't pursue or support action against anyone who reports a problem in good
faith, stays within their own account and test data, doesn't degrade the service
for others, and gives us reasonable time to fix it before publishing.

### Out of scope here

- **Swiggy's own platform and MCP server** — report those to Swiggy directly.
- **OpenAI, Google Sign-In, Twilio** — report to the provider.
- Volumetric denial of service, spam, or social engineering.
- Missing hardening headers with no demonstrated impact.

## How credentials are handled

- **Swiggy tokens are encrypted at rest** (Fernet, `backend/app/crypto.py`). The
  key lives outside the database, so a dump, backup or disk snapshot is inert on
  its own. The PKCE verifier is encrypted the same way.
- **Every user's own token is forwarded per request.** There is no shared service
  credential, and no user's token is ever used for another user's call.
- **We are a public OAuth client** (PKCE, no client secret), registered with
  Swiggy via Dynamic Client Registration.
- **No order is ever placed.** There is no order-placement endpoint in this
  codebase, and `backend/tests/test_cart.py` fails if `place_food_order`,
  `confirm_order` or `check_payment_status` is ever called. Swiping right builds
  a cart; the user completes checkout on Swiggy.
- **OAuth codes and states are redacted from logs** before they're written
  (`backend/app/middleware.py`).
- **Production refuses to start on a dev configuration** — a guessable signing
  key, a derived token-encryption key, console OTP delivery, the published
  compose database password, or a plain-http URL each stop the boot
  (`APP_ENV=prod`, `backend/app/config.py`).

Key rotation: `TOKEN_ENCRYPTION_KEY` accepts a comma-separated list. The first
key encrypts, all of them decrypt, so a key can be retired without disconnecting
users.

## Known limitations

We'd rather state these than have you find them.

- **Sessions can't be revoked server-side.** A session token is an HMAC-signed
  payload with a 30-day expiry; there's no deny-list, so the only way to
  invalidate every outstanding session is to rotate `SECRET_KEY`.
- **The device sign-in rate limiter is per-process and in memory.** It resets on
  restart and doesn't span workers. Correct for a single-instance deployment;
  a multi-worker one needs shared state.
- **Device sign-in creates unverified users.** A browser-generated id is enough
  for a session, which is a deliberate trade-off for a first-run demo. The id is
  accepted at that one endpoint and nowhere else.
- **Allergen filtering depends on the model's self-reported ingredients.**
  Suggestions are filtered against declared allergies more than once, but true
  zero-tolerance needs a verified ingredient source that neither we nor Swiggy
  expose today. This is stated in the README too, because users deserve to know
  it.
- **No in-app way to disconnect Swiggy, and no self-serve account deletion.**
  Both are handled by email today — see [PRIVACY.md](PRIVACY.md). A user can
  revoke this app from Swiggy's own account settings in the meantime, which
  takes effect immediately.

## Reporting a problem with an order

If something went wrong with an actual order, that's Swiggy's — use the Swiggy
app. We never take payment and never place orders.
