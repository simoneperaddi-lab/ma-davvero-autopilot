-- Run manually in the Supabase SQL editor. Backend service role only.
create table if not exists public.contents (
  id uuid primary key,
  created_at timestamptz not null default now(),
  payload jsonb not null
);
create index if not exists contents_created_at_idx on public.contents (created_at desc);
alter table public.contents enable row level security;
revoke all on public.contents from anon, authenticated;
grant select, insert on public.contents to service_role;
-- No public policies: never put the service role key in the dashboard.
