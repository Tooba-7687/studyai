# Runtime Validation Report

**Generated:** 2026-11-12
**Target:** StudyAI Django application (`C:\gauth-clone`)

## Summary

| Tier | Status | Exit code | Evidence |
|---|---|---:|---|
| Startup | PASS | 0 | Local Django login and dashboard loaded in the browser; signup and authenticated dashboard navigation worked. |
| Integration | PASS | 0 | 22 Django tests passed, including authentication, API validation, CSRF, user-data isolation, OCR input validation, and AI rate limiting. Django system checks passed; no migration drift. |
| Browser E2E | PARTIAL | 0 | Manual browser smoke flow: signup → dashboard → submit empty quiz → receive the expected HTTP 400 validation message. No AI-provider request was made. |
| Deployment security check | NEEDS SIGN-OFF | 0 | With debug disabled, a generated long secret, and HTTPS defaults, `check --deploy` reports only optional HSTS warnings (`security.W005`, `security.W021`). Enable subdomain/preload HSTS only after confirming the domain and all subdomains use HTTPS. |

**Overall:** NEEDS SIGN-OFF for production deployment; local/integration checks pass, but optional HSTS policy and automated browser coverage remain to be decided.

## Environment and test strategy

- **Database / infrastructure:** SQLite, Django's test database. Docker was unavailable (`docker` executable not found), and no Docker-dependent service is configured by this project.
- **Node.js:** unavailable (`node` executable not found).
- **Playwright:** automated Playwright setup was not possible without Node.js. The server-rendered app was manually smoke-tested in the integrated browser; this does not replace automated browser coverage.
- **Production security check:** HTTPS redirect, secure cookies, HSTS, and a random deployment secret were checked with debug disabled. The two remaining HSTS warnings are intentional until the deployment's subdomain and preload policy is known.
- **Test data:** Django `TestCase` creates and rolls back users and records; temporary browser-test users were deleted after the smoke test.
- **External AI calls:** tests mock Gemini calls or submit invalid input; the browser smoke test did not invoke Gemini.

## Fixes covered by regression tests

- Private history, flashcards, and saved plans are scoped to their owner; anonymous history is empty and anonymous clear-history does not delete user data.
- API writes use CSRF protection; both web frontends now send tokens.
- AI/OCR requests have a per-client rate limit; prompt sizes, quiz counts, image size/type, and study hours are validated before provider calls.
- Malformed/non-object JSON returns client errors instead of server errors; OCR errors no longer expose raw provider exception details.
- Existing history and flashcard records are preserved by nullable owner fields and are not exposed as another user's data.

## Remaining gaps

- The project previously had no automated tests; this change adds 22 Django tests, but broader feature coverage is still advisable.
- Browser validation was manual because Node.js was unavailable; install Node.js and add a Playwright suite for repeatable UI journeys.
- Before production deployment, configure a shared cache backend for rate limits when running multiple workers, set `DJANGO_DEBUG=False`, provide a unique `DJANGO_SECRET_KEY`, configure allowed hosts/CORS, and review hosting-specific security settings.
