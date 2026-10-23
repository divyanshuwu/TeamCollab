# TeamCollab deployment

## Deploy the frontend and API

Create two Vercel projects from this repository, using `frontend` as the frontend project's Root Directory and `backend` as the API project's Root Directory. Vercel detects Vite and the FastAPI `app` in `main.py`; the backend project serves the whole API through that single Python function, while the frontend builds to static files and uses no serverless functions. Add `VITE_API_BASE_URL` to the frontend project with the backend deployment URL (for example, `https://your-api.vercel.app`). Add `DATABASE_URL`, `JWT_SECRET_KEY`, `SUPABASE_URL`, and `SUPABASE_PUBLISHABLE_KEY` to the backend project; set `CORS_ORIGINS` to a comma-separated list of exact frontend origins, including any preview domains you plan to use. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` to the frontend project. Set Vercel project environment variables in the dashboard or CLI; the checked-in `.env.example` files contain placeholders only.
Create two Vercel projects from this repository, using `frontend` as the frontend project's Root Directory and `backend` as the API project's Root Directory. Vercel detects Vite and the FastAPI `app` in `main.py`; the backend project serves the whole API through that single Python function, while the frontend builds to static files and uses no serverless functions. Add `VITE_API_BASE_URL` to the frontend project with the backend deployment URL (for example, `https://your-api.vercel.app`). Add `DATABASE_URL`, `JWT_SECRET_KEY`, `SUPABASE_URL`, and `SUPABASE_PUBLISHABLE_KEY` to the backend project; set `CORS_ORIGINS` to a comma-separated list of exact frontend origins, including any preview origins you use. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` on the frontend project. Set Vercel project environment variables in the dashboard or CLI; the checked-in `.env.example` files contain placeholders only.

For database failover, set `AIVEN_DATABASE_URL` to the Aiven MySQL connection URI and `DB_SSL_CA=ca.pem`. If the primary `DATABASE_URL` cannot pass a `SELECT 1` check, the API uses the Aiven connection for that request. The Aiven database must already have the TeamCollab schema and current data. This connection fallback does not replicate writes between databases; keep the databases synchronized and manually move the primary back only after reconciling changes.

Before enabling Aiven auth fallback, apply `backend/aiven_add_auth_user_id.sql` to its existing `users` table. If Supabase Auth reports a network/DNS/server error, the frontend then uses the API's local password auth, which works only for users whose password hashes are present in the Aiven database. Supabase Auth users with no local password hash must wait for Supabase recovery.

## Supabase database

1. Create a Supabase project and run `supabase/migrations/20261022000000_initial_schema.sql` in its SQL Editor.
2. In Supabase, select **Connect** and choose the **Transaction pooler** for Vercel's serverless functions. Put that full connection URI in `DATABASE_URL`; URL-encode reserved characters in its password. Set `SUPABASE_URL` to the project URL and `SUPABASE_PUBLISHABLE_KEY` to its publishable key for backend token verification. Configure the frontend's `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` with the same project URL and publishable key.
3. Set `JWT_SECRET_KEY` to a private random value and optionally set `JWT_ALGORITHM` and `ACCESS_TOKEN_EXPIRE_MINUTES`.
4. Apply the same environment variables to local development through `backend/.env` (copy `backend/.env.example`). Never commit secrets.

This migration creates the PostgreSQL schema and a Supabase Auth user mapping column. It does not copy existing MySQL records. To migrate them, install `backend/migration-requirements.txt`, set `MYSQL_DATABASE_URL` to the current MySQL connection URI and `SUPABASE_MIGRATION_DATABASE_URL` to a Supabase Session Pooler URI, then run `python backend/migrate_mysql_to_supabase.py`. The target tables must be empty; the script copies rows in foreign-key order, preserves integer IDs and password hashes, and resets identity sequences. It refuses to merge into populated tables.

Supabase Auth does not import the existing Argon2 passwords. Users must register or reset their password through Supabase Auth using the same email so the API can link their existing TeamCollab records. Existing integer IDs are preserved by the copy script.

## Local run

Set `DATABASE_URL` and `JWT_SECRET_KEY`, install `backend/requirements.txt`, apply the schema, then start the API with `uvicorn main:app --app-dir backend --reload`. In `frontend/.env.local`, set `VITE_API_BASE_URL=http://127.0.0.1:8000` and the Supabase variables from `frontend/.env.example` and run `npm run dev` from `frontend`.

## API rate limits and database access

FastAPI applies shared, database-backed limits in two-hour windows. Defaults are 300 authenticated reads and 60 authenticated writes per user, 3 signup attempts per email and client IP, and 10 login attempts per email and client IP. The counts are configurable in `backend/.env` or the Vercel backend environment with `DB_READ_LIMIT_2H`, `DB_WRITE_LIMIT_2H`, `REGISTRATION_LIMIT_2H`, and `LOGIN_LIMIT_2H`. Responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset-After`; over-limit responses return 429 and `Retry-After`.

Before deploying this code, apply `supabase/migrations/20261023000000_api_rate_limits.sql` in the Supabase SQL Editor. If using Aiven as the active/fallback database, also apply `backend/aiven_rate_limits.sql` there. Rate limiting fails closed if the table is missing or its counter cannot be written. Set `RATE_LIMIT_HMAC_KEY` to a private random value (or use the existing private `JWT_SECRET_KEY` fallback); the counters store keyed hashes rather than emails or user IDs.

The Vite client has no database credentials or direct table access; it sends app data requests to FastAPI. Protected API routes verify the bearer token before opening a database session, and project/task/member queries enforce ownership or membership checks. The migration enables RLS and revokes Supabase client-role access to the app tables and rate-limit table; FastAPI uses the private server-side database connection. Signup through the website reserves an API registration attempt before calling Supabase Auth. Direct calls to Supabase Auth remain subject to Supabase's own rate limits, including its separate email-sending quota.

## Supabase browser client

The Vite frontend has `@supabase/supabase-js` configured in `frontend/src/utils/supabase.js`. For local development, the provided project URL and publishable key are in the ignored `frontend/.env.local`; copy the variable names from `frontend/.env.example` into Vercel's frontend environment settings as well.

The frontend now uses Supabase Auth for registration and sign-in; FastAPI verifies Supabase access tokens and maps Auth identities to application users. App data continues to flow through FastAPI to Postgres, so the publishable key is not used for unrestricted direct table queries. The sample `todos` table does not exist in this application.

In Supabase **Authentication → URL Configuration**, set the production frontend URL as the Site URL and add the production and local frontend URLs to Redirect URLs. Enable email/password sign-in. If email confirmation is enabled, registration asks users to confirm by email before signing in.
