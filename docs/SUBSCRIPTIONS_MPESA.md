# SFW subscriptions and M-Pesa deployment

This feature is developed on the `feature/sfw-subscriptions-mpesa` branch. It preserves the public SFW research workspace: registration is optional for public tools, while an account is required only for billing.

## Published plan catalogue

| Plan | Price | Billing |
|---|---:|---|
| Free | KES 0 | No charge |
| Student | KES 299 | Monthly |
| Pro Researcher | KES 699 | Monthly |
| Educator | KES 1,499 | Monthly |
| Institution | Custom quotation | Contact SFW |

The prices are the approved starting catalogue. Specific premium feature limits have deliberately not been invented in this release. The current code records the selected plan and verified subscription status; it does not yet gate individual research tools by tier. Automatic renewals are disabled.

## Deployment order

1. Back up the Supabase database before changing anything.
2. In the Supabase SQL Editor, verify that the existing base objects are present: `sfw_projects`, `sfw_login_events`, and `public.sfw_touch_updated_at()`. If the project is genuinely new and these objects are absent, apply `supabase/schema.sql` first and `supabase/login_audit.sql` second. Do not rerun the login-audit script just to install billing; it also contains administrator-role updates.
3. Run `supabase/subscriptions.sql` in the SQL Editor.
4. Run `supabase/mpesa_functions.sql` in the SQL Editor.
5. From the repository root, deploy the Edge Functions:
   ```powershell
   npx supabase functions deploy mpesa-stk-push
   npx supabase functions deploy mpesa-callback
   ```
6. Register the callback URL with the Daraja application:
   `https://YOUR_PROJECT_REF.supabase.co/functions/v1/mpesa-callback`
7. Add the server secrets listed below in Supabase Dashboard → Edge Functions → Secrets.
8. Enable the Supabase Cron extension if it is not already enabled, then schedule `select public.sfw_expire_subscriptions();` once daily (for example, 00:15 UTC). The function revokes execution from public, anon and authenticated roles; schedule it as the database owner, not as an ordinary user. Do not expose it to public clients.
9. Start in Daraja sandbox. Complete a full STK test and verify the payment, receipt, subscription dates and user history before switching to production.
10. Deploy the Streamlit app from the feature branch only after local tests and Edge Function checks pass.

## Edge Function secrets

Set these in Supabase Edge Function Secrets. Do not put them in Streamlit Secrets, GitHub, source code or screenshots.

- `MPESA_ENV`: `sandbox` for testing; `production` only after approval and successful tests.
- `MPESA_CONSUMER_KEY`: Daraja app consumer key.
- `MPESA_CONSUMER_SECRET`: Daraja app consumer secret.
- `MPESA_BUSINESS_SHORTCODE`: the registered PayBill or Till shortcode.
- `MPESA_PASSKEY`: Daraja Lipa Na M-Pesa passkey for the shortcode.
- `MPESA_CALLBACK_URL`: the public HTTPS URL of the deployed `mpesa-callback` function.
- `MPESA_TRANSACTION_TYPE`: `CustomerPayBillOnline` for PayBill or `CustomerBuyGoodsOnline` for Till.

Supabase provides its project URL and server key to Edge Functions. The code supports the current `SUPABASE_SECRET_KEYS` / `SUPABASE_PUBLISHABLE_KEYS` maps and legacy environment names. A secret/service-role key must never be exposed to Streamlit or the browser.

## Payment flow

1. A signed-in user chooses a monthly plan and supplies a Kenyan mobile number.
2. The authenticated `mpesa-stk-push` function verifies the Supabase user, reads the amount from the database plan row, creates pending records and requests an STK Push.
3. The user completes or cancels the prompt on the phone.
4. Daraja posts to `mpesa-callback`. The callback function looks up the matching checkout and queries Daraja directly before it can activate a subscription.
5. The database finalisation function atomically marks the payment successful and activates the linked subscription for one month. Duplicate success callbacks are idempotent.
6. Users can view only their own subscription and payment history. Administrators can view all records through RLS policies.

Daraja STK callbacks do not provide a cryptographic signature in this integration. The callback is therefore not trusted on its own: SFW performs a server-to-server STK Query and checks the checkout reference, amount, phone and receipt before granting access. Failed or unconfirmed queries are not treated as successful payments.

## Important current limitations

- The subscription feature is not live until the SQL migrations, Edge Function secrets and deployments are completed.
- Sandbox credentials and test transactions are required before production use.
- Feature-specific premium limits, entitlement enforcement, cancellations, refunds, renewal reminders and automatic recurring payments are not implemented in this first billing foundation. Subscription expiry is implemented as a server-only database routine and requires a trusted daily schedule to run.
- Institutions use a custom quotation; there is no self-service institution checkout.
- Do not represent an STK prompt as a completed payment. Only a server-verified successful callback activates the subscription.
