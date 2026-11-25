-- SFW subscription and payment foundation.
-- Run after schema.sql and login_audit.sql in the Supabase SQL Editor.
-- Payment creation, callback verification and subscription activation must run
-- server-side with a Supabase service-role key. Never place that key in Streamlit.

create table if not exists public.sfw_plans (
    code text primary key check (code ~ '^[a-z][a-z0-9_]{1,39}$'),
    name text not null,
    amount_kes integer,
    billing_interval text not null default 'month'
        check (billing_interval in ('month', 'custom', 'none')),
    description text not null default '',
    entitlements jsonb not null default '{}'::jsonb,
    is_public boolean not null default true,
    is_active boolean not null default true,
    sort_order integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (amount_kes is null or amount_kes >= 0),
    check (
        (code = 'institution' and billing_interval = 'custom')
        or (code = 'free' and billing_interval = 'none' and amount_kes = 0)
        or (code not in ('institution', 'free') and billing_interval = 'month' and amount_kes > 0)
    )
);

insert into public.sfw_plans
    (code, name, amount_kes, billing_interval, description, entitlements, sort_order)
values
    ('free', 'Free', 0, 'none',
     'Open access to the core SFW research workspace.',
     '{"access_level":"free"}'::jsonb, 0),
    ('student', 'Student', 299, 'month',
     'Affordable monthly access for individual student researchers.',
     '{"access_level":"student"}'::jsonb, 1),
    ('pro_researcher', 'Pro Researcher', 699, 'month',
     'Expanded monthly access for independent researchers.',
     '{"access_level":"pro"}'::jsonb, 2),
    ('educator', 'Educator', 1499, 'month',
     'Monthly access for educators supporting research and learning.',
     '{"access_level":"educator"}'::jsonb, 3),
    ('institution', 'Institution', null, 'custom',
     'Custom arrangements for schools, universities and research organisations.',
     '{"access_level":"institution"}'::jsonb, 4)
on conflict (code) do update set
    name = excluded.name,
    amount_kes = excluded.amount_kes,
    billing_interval = excluded.billing_interval,
    description = excluded.description,
    sort_order = excluded.sort_order,
    updated_at = now();

create table if not exists public.sfw_subscriptions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    plan_code text not null references public.sfw_plans(code),
    status text not null default 'pending'
        check (status in ('pending', 'active', 'past_due', 'cancelled', 'expired')),
    starts_at timestamptz,
    ends_at timestamptz,
    auto_renew boolean not null default false,
    provider text not null default 'manual'
        check (provider in ('manual', 'mpesa')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (ends_at is null or starts_at is null or ends_at > starts_at)
);

create index if not exists sfw_subscriptions_user_status_idx
    on public.sfw_subscriptions (user_id, status, ends_at desc);

create table if not exists public.sfw_payment_transactions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    subscription_id uuid references public.sfw_subscriptions(id) on delete set null,
    provider text not null default 'mpesa' check (provider in ('mpesa', 'manual')),
    amount_kes integer not null check (amount_kes > 0),
    currency text not null default 'KES' check (currency = 'KES'),
    phone_number text,
    merchant_request_id text,
    checkout_request_id text unique,
    mpesa_receipt_number text unique,
    idempotency_key text unique,
    status text not null default 'pending'
        check (status in ('pending', 'success', 'failed', 'cancelled')),
    provider_result_code text,
    provider_result_description text,
    callback_payload jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sfw_payments_user_created_idx
    on public.sfw_payment_transactions (user_id, created_at desc);
create index if not exists sfw_payments_status_created_idx
    on public.sfw_payment_transactions (status, created_at desc);

alter table public.sfw_plans enable row level security;
alter table public.sfw_subscriptions enable row level security;
alter table public.sfw_payment_transactions enable row level security;

drop policy if exists "Public can read active SFW plans" on public.sfw_plans;
create policy "Public can read active SFW plans"
    on public.sfw_plans for select to anon, authenticated
    using (is_active and is_public);

drop policy if exists "Users can read their own SFW subscriptions" on public.sfw_subscriptions;
create policy "Users can read their own SFW subscriptions"
    on public.sfw_subscriptions for select to authenticated
    using (auth.uid() = user_id);

drop policy if exists "Admins can read all SFW subscriptions" on public.sfw_subscriptions;
create policy "Admins can read all SFW subscriptions"
    on public.sfw_subscriptions for select to authenticated
    using ((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

drop policy if exists "Users can read their own SFW payments" on public.sfw_payment_transactions;
create policy "Users can read their own SFW payments"
    on public.sfw_payment_transactions for select to authenticated
    using (auth.uid() = user_id);

drop policy if exists "Admins can read all SFW payments" on public.sfw_payment_transactions;
create policy "Admins can read all SFW payments"
    on public.sfw_payment_transactions for select to authenticated
    using ((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- Clients receive read-only access. Trusted server-side code using the
-- service-role key performs payment inserts/updates and subscription changes.
revoke all on public.sfw_plans from anon, authenticated;
grant select on public.sfw_plans to anon, authenticated;
revoke all on public.sfw_subscriptions from anon, authenticated;
grant select on public.sfw_subscriptions to authenticated;
revoke all on public.sfw_payment_transactions from anon, authenticated;
grant select on public.sfw_payment_transactions to authenticated;

drop trigger if exists sfw_plans_touch_updated_at on public.sfw_plans;
create trigger sfw_plans_touch_updated_at
before update on public.sfw_plans
for each row execute function public.sfw_touch_updated_at();

drop trigger if exists sfw_subscriptions_touch_updated_at on public.sfw_subscriptions;
create trigger sfw_subscriptions_touch_updated_at
before update on public.sfw_subscriptions
for each row execute function public.sfw_touch_updated_at();

drop trigger if exists sfw_payments_touch_updated_at on public.sfw_payment_transactions;
create trigger sfw_payments_touch_updated_at
before update on public.sfw_payment_transactions
for each row execute function public.sfw_touch_updated_at();
