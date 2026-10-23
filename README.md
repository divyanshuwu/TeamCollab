# TeamCollab deployment

## Deploy the frontend and API

Create two Vercel projects from this repository, using `frontend` as the frontend project's Root Directory and `backend` as the API project's Root Directory. Vercel detects Vite and the FastAPI `app` in `main.py`; the backend project serves the whole API through that single Python function, while the frontend builds to static files and uses no serverless functions. Add `VITE_API_BASE_URL` to the frontend project with the backend deployment URL (for example, `https://your-api.vercel.app`). Add `DATABASE_URL`, `JWT_SECRET_KEY`, `SUPABASE_URL`, and `SUPABASE_PUBLISHABLE_KEY` to the backend project; set `CORS_ORIGINS` to a comma-separated list of exact frontend origins, including any preview domains you plan to use. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` to the frontend project. Set Vercel project environment variables in the dashboard or CLI; the checked-in `.env.example` files contain placeholders only.

## Supabase database

1. Create a Supabase project and run `supabase/migrations/20261022000000_initial_schema.sql` in its SQL Editor.
2. In Supabase, select **Connect** and choose the **Transaction pooler** for Vercel's serverless functions. Put that full connection URI in `DATABASE_URL`; URL-encode reserved characters in its password. Set `SUPABASE_URL` to the project URL and `SUPABASE_PUBLISHABLE_KEY` to its publishable key for backend token verification.
3. Set `JWT_SECRET_KEY` to a private random value and optionally set `JWT_ALGORITHM` and `ACCESS_TOKEN_EXPIRE_MINUTES`.
4. Apply the same environment variables to local development through `backend/.env` (copy `backend/.env.example`). Never commit secrets.

This migration creates the PostgreSQL schema and a Supabase Auth user mapping column. It does not copy existing MySQL records. To migrate them, install `backend/migration-requirements.txt`, set `MYSQL_DATABASE_URL` to the current MySQL connection URI and `SUPABASE_MIGRATION_DATABASE_URL` to a Supabase Session Pooler URI, then run `python backend/migrate_mysql_to_supabase.py`. The target tables must be empty; the script copies rows in foreign-key order, preserves integer IDs and password hashes, and resets identity sequences. It refuses to merge into populated tables.

Supabase Auth does not import the existing Argon2 passwords. Users must register or reset their password through Supabase Auth using the same email so the API can link their existing TeamCollab records. Existing integer IDs are preserved by the copy script.

## Local run

Set `DATABASE_URL` and `JWT_SECRET_KEY`, install `backend/requirements.txt`, apply the schema, then start the API with `uvicorn main:app --app-dir backend --reload`. In `frontend/.env.local`, set `VITE_API_BASE_URL=http://127.0.0.1:8000` and the Supabase variables from `frontend/.env.example` and run `npm run dev` from `frontend`.

## Supabase browser client

The Vite frontend has `@supabase/supabase-js` configured in `frontend/src/utils/supabase.js`. For local development, the provided project URL and publishable key are in the ignored `frontend/.env.local`; copy the variable names from `frontend/.env.example` into Vercel's frontend environment settings as well.

The frontend now uses Supabase Auth for registration and sign-in; FastAPI verifies Supabase access tokens and maps Auth identities to application users. App data continues to flow through FastAPI to Postgres, so the publishable key is not used for unrestricted direct table queries. The sample `todos` table does not exist in this application.

In Supabase **Authentication → URL Configuration**, set the production frontend URL as the Site URL and add the production and local frontend URLs to Redirect URLs. Enable email/password sign-in. If email confirmation is enabled, registration asks users to confirm by email before signing in.
