import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function required(name: string): string {
  const value = Deno.env.get(name)?.trim();
  if (!value) throw new Error(`Missing server configuration: ${name}`);
  return value;
}

function normaliseKenyanPhone(input: unknown): string {
  const digits = String(input ?? "").replace(/[\s()+-]/g, "");
  let phone = digits;
  if (/^0[17]\d{8}$/.test(phone)) phone = `254${phone.slice(1)}`;
  if (/^\+[17]\d{10}$/.test(String(input ?? "").replace(/[\s()-]/g, ""))) {
    phone = String(input).replace(/[\s()-]/g, "").slice(1);
    phone = `254${phone.slice(-9)}`;
  }
  if (!/^254[17]\d{8}$/.test(phone)) {
    throw new Error("Enter a valid Kenyan Safaricom number, for example 0712345678.");
  }
  return phone;
}

function darajaTimestamp(): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Nairobi",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}${values.month}${values.day}${values.hour}${values.minute}${values.second}`;
}

async function getDarajaToken(baseUrl: string): Promise<string> {
  const key = required("MPESA_CONSUMER_KEY");
  const secret = required("MPESA_CONSUMER_SECRET");
  const credentials = btoa(`${key}:${secret}`);
  const response = await fetch(
    `${baseUrl}/oauth/v1/generate?grant_type=client_credentials`,
    { headers: { Authorization: `Basic ${credentials}` } },
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    throw new Error("Could not authenticate with M-Pesa Daraja.");
  }
  return data.access_token as string;
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json({ error: "Method not allowed." }, 405);

  let admin: any;
  let subscriptionId: string | undefined;
  let paymentId: string | undefined;
  let checkoutRequestId: string | undefined;
  let stkAccepted = false;

  try {
    const authorization = request.headers.get("Authorization") ?? "";
    const accessToken = authorization.replace(/^Bearer\s+/i, "");
    if (!accessToken || accessToken === authorization) {
      return json({ error: "Please sign in before starting a payment." }, 401);
    }

    const supabaseUrl = required("SUPABASE_URL");
    const publishableMap = Deno.env.get("SUPABASE_PUBLISHABLE_KEYS");
    const publishableKey = publishableMap
      ? JSON.parse(publishableMap).default
      : Deno.env.get("SUPABASE_ANON_KEY")
        ?? Deno.env.get("SUPABASE_PUBLISHABLE_KEY")
        ?? "";
    const secretMap = Deno.env.get("SUPABASE_SECRET_KEYS");
    const secretKey = secretMap
      ? JSON.parse(secretMap).default
      : Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!publishableKey || !secretKey) {
      throw new Error("Supabase server keys are not configured for this function.");
    }

    const userClient = createClient(supabaseUrl, publishableKey, {
      auth: { persistSession: false, autoRefreshToken: false },
      global: { headers: { Authorization: `Bearer ${accessToken}` } },
    });
    const { data: userData, error: userError } = await userClient.auth.getUser(accessToken);
    if (userError || !userData.user) return json({ error: "Your session is invalid. Sign in again." }, 401);

    const body = await request.json();
    const planCode = String(body?.plan_code ?? "").trim().toLowerCase();
    const phone = normaliseKenyanPhone(body?.phone_number);

    admin = createClient(supabaseUrl, secretKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const { data: plan, error: planError } = await admin
      .from("sfw_plans")
      .select("code,name,amount_kes,billing_interval,is_active")
      .eq("code", planCode)
      .eq("is_active", true)
      .single();
    if (planError || !plan || plan.billing_interval !== "month" || !Number.isInteger(plan.amount_kes) || plan.amount_kes <= 0) {
      return json({ error: "This plan is not available for online monthly payment." }, 400);
    }

    const { data: subscription, error: subscriptionError } = await admin
      .from("sfw_subscriptions")
      .insert({
        user_id: userData.user.id,
        plan_code: plan.code,
        status: "pending",
        provider: "mpesa",
        auto_renew: false,
      })
      .select("id")
      .single();
    if (subscriptionError || !subscription) throw new Error("Could not create a pending subscription.");
    subscriptionId = subscription.id;

    const { data: payment, error: paymentError } = await admin
      .from("sfw_payment_transactions")
      .insert({
        user_id: userData.user.id,
        subscription_id: subscriptionId,
        provider: "mpesa",
        amount_kes: plan.amount_kes,
        currency: "KES",
        phone_number: phone,
        status: "pending",
        idempotency_key: crypto.randomUUID(),
      })
      .select("id")
      .single();
    if (paymentError || !payment) throw new Error("Could not create a pending payment record.");
    paymentId = payment.id;

    const environment = (Deno.env.get("MPESA_ENV") ?? "sandbox").toLowerCase();
    if (!["sandbox", "production"].includes(environment)) throw new Error("MPESA_ENV must be sandbox or production.");
    const baseUrl = environment === "production"
      ? "https://api.safaricom.co.ke"
      : "https://sandbox.safaricom.co.ke";
    const shortcode = required("MPESA_BUSINESS_SHORTCODE");
    const passkey = required("MPESA_PASSKEY");
    const callbackUrl = required("MPESA_CALLBACK_URL");
    if (!callbackUrl.startsWith("https://")) throw new Error("MPESA_CALLBACK_URL must use HTTPS.");

    const timestamp = darajaTimestamp();
    const password = btoa(`${shortcode}${passkey}${timestamp}`);
    const token = await getDarajaToken(baseUrl);
    const transactionType = Deno.env.get("MPESA_TRANSACTION_TYPE") ?? "CustomerPayBillOnline";
    if (!["CustomerPayBillOnline", "CustomerBuyGoodsOnline"].includes(transactionType)) {
      throw new Error("MPESA_TRANSACTION_TYPE is invalid.");
    }

    const stkResponse = await fetch(`${baseUrl}/mpesa/stkpush/v1/processrequest`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        BusinessShortCode: shortcode,
        Password: password,
        Timestamp: timestamp,
        TransactionType: transactionType,
        Amount: plan.amount_kes,
        PartyA: phone,
        PartyB: shortcode,
        PhoneNumber: phone,
        CallBackURL: callbackUrl,
        AccountReference: `SFW${paymentId.replace(/-/g, "").slice(0, 9)}`,
        TransactionDesc: `SFW ${plan.name}`.slice(0, 13),
      }),
    });
    const stk = await stkResponse.json().catch(() => ({}));
    if (!stkResponse.ok || String(stk.ResponseCode) !== "0" || !stk.CheckoutRequestID) {
      throw new Error(String(stk.errorMessage ?? stk.ResponseDescription ?? "M-Pesa did not accept the payment request."));
    }
    checkoutRequestId = String(stk.CheckoutRequestID);
    stkAccepted = true;

    const { error: updateError } = await admin
      .from("sfw_payment_transactions")
      .update({
        merchant_request_id: stk.MerchantRequestID ?? null,
        checkout_request_id: checkoutRequestId,
        provider_result_code: String(stk.ResponseCode),
        provider_result_description: String(stk.ResponseDescription ?? "STK prompt accepted"),
      })
      .eq("id", paymentId);
    if (updateError) throw new Error("M-Pesa accepted the request, but SFW could not save its checkout reference. Contact support before retrying.");

    return json({
      ok: true,
      message: "Payment prompt sent. Enter your M-Pesa PIN on your phone to complete payment.",
      checkout_request_id: stk.CheckoutRequestID,
      amount_kes: plan.amount_kes,
      plan_name: plan.name,
    });
  } catch (error) {
    if (admin && paymentId && stkAccepted && checkoutRequestId) {
      // The customer may already have an STK prompt. Preserve the pending
      // transaction and retry saving its checkout reference; never mark it failed.
      const { error: recoveryError } = await admin.from("sfw_payment_transactions")
        .update({
          checkout_request_id: checkoutRequestId,
          provider_result_description: "STK prompt accepted; checkout reference recovery pending",
        })
        .eq("id", paymentId);
      if (recoveryError) {
        return json({
          error: `M-Pesa sent the prompt, but SFW could not save its reference. Do not retry payment. Contact support with reference ${checkoutRequestId}.`,
        }, 502);
      }
      return json({
        error: `M-Pesa sent the prompt. Complete it on your phone; do not start another payment. Reference: ${checkoutRequestId}.`,
      }, 502);
    }
    if (admin && paymentId) {
      await admin.from("sfw_payment_transactions")
        .update({ status: "failed", provider_result_description: String(error).slice(0, 500) })
        .eq("id", paymentId)
        .eq("status", "pending");
    }
    if (admin && subscriptionId) {
      await admin.from("sfw_subscriptions")
        .update({ status: "cancelled" })
        .eq("id", subscriptionId)
        .eq("status", "pending");
    }
    return json({ error: error instanceof Error ? error.message : "Payment could not be started." }, 400);
  }
});
