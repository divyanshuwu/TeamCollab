-- Shared database-backed limits for the FastAPI application.
-- Apply in the Supabase SQL Editor before deploying the rate-limit code.
create table if not exists public.api_rate_limits (
  key_hash varchar(64) primary key,
  window_started_at timestamp without time zone not null,
  request_count integer not null default 0
);

-- The table contains keyed hashes only. Client roles must not access it;
-- FastAPI connects with the private server-side database URL.
alter table public.api_rate_limits enable row level security;
revoke all on table public.api_rate_limits from public, anon, authenticated, service_role;

-- Application tables are accessed only by FastAPI using its private database
-- connection. The browser's publishable key must not query them directly.
alter table public.users enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.tasks enable row level security;

revoke all on table public.users, public.projects,
  public.project_members, public.tasks
  from public, anon, authenticated, service_role;
