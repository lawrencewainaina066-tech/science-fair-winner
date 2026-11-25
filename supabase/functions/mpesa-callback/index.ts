import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

function required(name: string): string {
  const value = Deno.env.get(name)?.trim();
  if (!value) throw new Error(`Missing server configuration: ${name}`);
  return value;
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
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

async function darajaToken(baseUrl: string): Promise<string> {
  const credentials = btoa(
    `${required("MPESA_CONSUMER_KEY")}:${required("MPESA_CONSUMER_SECRET")}`,
  );
  const response = await fetch(
    `${baseUrl}/oauth/v1/generate?grant_type=client_credentials`,
    { headers: { Authorization: `Basic ${credentials}` } },
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) throw new Error("Daraja OAuth failed.");
  return data.access_token as string;
}

Deno.serve(async (request) => {
  if (request.method !== "POST") return json({ error: "Method not allowed." }, 405);

  try {
    const payload = await request.json();
    const callback = payload?.Body?.stkCallback;
    const checkoutId = String(callback?.CheckoutRequestID ?? "").trim();
    if (!checkoutId) return json({ error: "Missing checkout reference." }, 400);

    const supabaseUrl = required("SUPABASE_URL");
    const secretMap = Deno.env.get("SUPABASE_SECRET_KEYS");
    const secretKey = secretMap
      ? JSON.parse(secretMap).default
      : Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!secretKey) throw new Error("Supabase server secret is not configured.");

    const admin = createClient(supabaseUrl, secretKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const { data: payment, error: paymentError } = await admin
      .from("sfw_payment_transactions")
      .select("id,user_id,subscription_id,amount_kes,phone_number,status")
      .eq("checkout_request_id", checkoutId)
      .maybeSingle();
    if (paymentError) throw new Error("Could not locate the SFW payment record.");
    if (!payment) return json({ error: "Unknown checkout reference." }, 404);
    if (payment.status === "success") {
      return json({ ResultCode: 0, ResultDesc: "Payment already confirmed." });
    }
    if (payment.status !== "pending") {
      return json({ ResultCode: 0, ResultDesc: "Payment is already closed." });
    }

    const metadataItems = callback?.CallbackMetadata?.Item ?? [];
    const metadata = Object.fromEntries(
      metadataItems.map((item: { Name: string; Value?: unknown }) => [item.Name, item.Value]),
    );
    const callbackAmount = Number(metadata.Amount);
    const receipt = String(metadata.MpesaReceiptNumber ?? "").trim();
    const callbackPhone = String(metadata.PhoneNumber ?? "").trim();
    const callbackResultCode = Number(callback?.ResultCode);

    const environment = (Deno.env.get("MPESA_ENV") ?? "sandbox").toLowerCase();
    if (!["sandbox", "production"].includes(environment)) throw new Error("MPESA_ENV is invalid.");
    const baseUrl = environment === "production"
      ? "https://api.safaricom.co.ke"
      : "https://sandbox.safaricom.co.ke";
    const shortcode = required("MPESA_BUSINESS_SHORTCODE");
    const passkey = required("MPESA_PASSKEY");
    const timestamp = darajaTimestamp();
    const password = btoa(`${shortcode}${passkey}${timestamp}`);
    const token = await darajaToken(baseUrl);

    // Daraja callbacks are not cryptographically signed. Query the checkout
    // directly with Daraja before granting access; never trust a browser claim.
    const queryResponse = await fetch(`${baseUrl}/mpesa/stkpushquery/v1/query`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        BusinessShortCode: shortcode,
        Password: password,
        Timestamp: timestamp,
        CheckoutRequestID: checkoutId,
      }),
    });
    const query = await queryResponse.json().catch(() => ({}));
    if (!queryResponse.ok || String(query.ResponseCode) !== "0" || query.ResultCode === undefined) {
      // Leave the record pending if Daraja cannot independently confirm its state.
      return json({ error: "Daraja could not verify the checkout yet." }, 503);
    }

    const verifiedResultCode = Number(query.ResultCode);
    if (verifiedResultCode !== 0 || callbackResultCode !== 0) {
      const { error } = await admin.rpc("sfw_fail_mpesa_payment", {
        p_checkout_request_id: checkoutId,
        p_result_code: String(verifiedResultCode),
        p_result_description: String(query.ResultDesc ?? callback?.ResultDesc ?? "Payment not completed"),
      });
      if (error) throw new Error("Could not record the verified failed payment.");
      return json({ ResultCode: 0, ResultDesc: "Payment failure recorded." });
    }

    if (!Number.isFinite(callbackAmount) || callbackAmount !== payment.amount_kes ||
        !receipt || callbackPhone !== payment.phone_number) {
      return json({ error: "Callback details did not match the SFW payment record." }, 400);
    }

    const { data: confirmation, error: confirmError } = await admin.rpc(
      "sfw_confirm_mpesa_payment",
      {
        p_checkout_request_id: checkoutId,
        p_receipt_number: receipt,
        p_phone_number: callbackPhone,
        p_amount_kes: callbackAmount,
      },
    );
    if (confirmError || !confirmation?.confirmed) {
      throw new Error("Daraja verified the payment, but SFW could not activate the subscription.");
    }

    return json({ ResultCode: 0, ResultDesc: "Payment verified and subscription activated." });
  } catch (_error) {
    // Avoid returning secrets, provider payloads or internal exception details to the webhook caller.
    return json({ error: "SFW could not process this callback. The payment remains available for reconciliation." }, 500);
  }
});
