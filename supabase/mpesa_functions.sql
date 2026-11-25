-- Atomic M-Pesa payment finalisation helpers.
-- Run after supabase/subscriptions.sql.
-- These functions are callable only by trusted Supabase service-role code.

create or replace function public.sfw_confirm_mpesa_payment(
    p_checkout_request_id text,
    p_receipt_number text,
    p_phone_number text,
    p_amount_kes integer
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_payment public.sfw_payment_transactions%rowtype;
    v_subscription public.sfw_subscriptions%rowtype;
begin
    if coalesce(auth.role(), '') <> 'service_role' then
        raise exception 'Service role required';
    end if;

    if nullif(trim(p_checkout_request_id), '') is null
       or nullif(trim(p_receipt_number), '') is null
       or p_amount_kes is null or p_amount_kes <= 0 then
        raise exception 'Invalid payment confirmation data';
    end if;

    select * into v_payment
    from public.sfw_payment_transactions
    where checkout_request_id = p_checkout_request_id
    for update;

    if not found then
        raise exception 'Payment transaction not found';
    end if;

    if v_payment.status = 'success' then
        return jsonb_build_object('confirmed', true, 'already_confirmed', true);
    end if;

    if v_payment.status <> 'pending' then
        raise exception 'Payment is not pending';
    end if;

    if v_payment.amount_kes <> p_amount_kes then
        raise exception 'Payment amount does not match';
    end if;

    if v_payment.subscription_id is null then
        raise exception 'Payment has no linked subscription';
    end if;

    select * into v_subscription
    from public.sfw_subscriptions
    where id = v_payment.subscription_id
      and user_id = v_payment.user_id
    for update;

    if not found or v_subscription.plan_code = 'free' then
        raise exception 'Linked subscription is invalid';
    end if;

    update public.sfw_payment_transactions
    set status = 'success',
        mpesa_receipt_number = trim(p_receipt_number),
        phone_number = coalesce(nullif(trim(p_phone_number), ''), phone_number),
        provider_result_code = '0',
        provider_result_description = 'Payment confirmed by Daraja STK query',
        updated_at = now()
    where id = v_payment.id;

    update public.sfw_subscriptions
    set status = 'active',
        provider = 'mpesa',
        starts_at = now(),
        ends_at = now() + interval '1 month',
        auto_renew = false,
        updated_at = now()
    where id = v_subscription.id;

    return jsonb_build_object(
        'confirmed', true,
        'already_confirmed', false,
        'subscription_id', v_subscription.id
    );
end;
$$;

create or replace function public.sfw_fail_mpesa_payment(
    p_checkout_request_id text,
    p_result_code text,
    p_result_description text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
    if coalesce(auth.role(), '') <> 'service_role' then
        raise exception 'Service role required';
    end if;

    update public.sfw_payment_transactions
    set status = 'failed',
        provider_result_code = left(coalesce(p_result_code, 'failed'), 80),
        provider_result_description = left(coalesce(p_result_description, 'Payment failed'), 500),
        updated_at = now()
    where checkout_request_id = p_checkout_request_id
      and status = 'pending';

    return found;
end;
$$;

revoke all on function public.sfw_confirm_mpesa_payment(text, text, text, integer) from public, anon, authenticated;
revoke all on function public.sfw_fail_mpesa_payment(text, text, text) from public, anon, authenticated;
grant execute on function public.sfw_confirm_mpesa_payment(text, text, text, integer) to service_role;
grant execute on function public.sfw_fail_mpesa_payment(text, text, text) to service_role;
