-- Run this SQL in the Supabase SQL Editor for your SFW project.
-- Do not create or expose a service_role key in the Streamlit application.

create table if not exists public.sfw_projects (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 1 and 200),
    payload jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sfw_projects_user_updated_idx
    on public.sfw_projects (user_id, updated_at desc);

alter table public.sfw_projects enable row level security;

drop policy if exists "Users can read their own SFW projects" on public.sfw_projects;
create policy "Users can read their own SFW projects"
    on public.sfw_projects for select to authenticated
    using (auth.uid() = user_id);

drop policy if exists "Users can create their own SFW projects" on public.sfw_projects;
create policy "Users can create their own SFW projects"
    on public.sfw_projects for insert to authenticated
    with check (auth.uid() = user_id);

drop policy if exists "Users can update their own SFW projects" on public.sfw_projects;
create policy "Users can update their own SFW projects"
    on public.sfw_projects for update to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own SFW projects" on public.sfw_projects;
create policy "Users can delete their own SFW projects"
    on public.sfw_projects for delete to authenticated
    using (auth.uid() = user_id);

grant select, insert, update, delete on public.sfw_projects to authenticated;

create or replace function public.sfw_touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists sfw_projects_touch_updated_at on public.sfw_projects;
create trigger sfw_projects_touch_updated_at
before update on public.sfw_projects
for each row execute function public.sfw_touch_updated_at();
