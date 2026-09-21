-- Screener SPC: Recommendations database (Supabase)
create table if not exists public.recommendations (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  entry_min numeric not null,
  entry_max numeric not null,
  tp1 numeric not null,
  tp2 numeric not null,
  sl numeric not null,
  note text default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by uuid references auth.users(id)
);

create index if not exists recommendations_created_at_idx
  on public.recommendations (created_at desc);

alter table public.recommendations enable row level security;

drop policy if exists "Public can read recommendations" on public.recommendations;
create policy "Public can read recommendations"
  on public.recommendations for select
  using (true);

drop policy if exists "Authenticated can insert recommendations" on public.recommendations;
create policy "Authenticated can insert recommendations"
  on public.recommendations for insert
  to authenticated
  with check (auth.uid() = created_by);

drop policy if exists "Authenticated can update recommendations" on public.recommendations;
create policy "Authenticated can update recommendations"
  on public.recommendations for update
  to authenticated
  using (auth.uid() = created_by)
  with check (auth.uid() = created_by);

drop policy if exists "Authenticated can delete recommendations" on public.recommendations;
create policy "Authenticated can delete recommendations"
  on public.recommendations for delete
  to authenticated
  using (auth.uid() = created_by);

create or replace function public.set_recommendation_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists recommendations_updated_at on public.recommendations;
create trigger recommendations_updated_at
before update on public.recommendations
for each row execute function public.set_recommendation_updated_at();

-- After creating the table, create your admin account in
-- Supabase Dashboard -> Authentication -> Users.
