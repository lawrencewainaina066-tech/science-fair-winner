import { DurableObject } from "cloudflare:workers";

const PORT = 8501;
const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;

interface Env {
  SFW_CONTAINER: DurableObjectNamespace<SFWContainer>;
  R2_ACCOUNT_ID?: string;
  R2_BUCKET_NAME?: string;
  AWS_ACCESS_KEY_ID?: string;
  AWS_SECRET_ACCESS_KEY?: string;
  SFW_AI_PROVIDER?: string;
  ANTHROPIC_API_KEY?: string;
  ANTHROPIC_MODEL?: string;
  OPENAI_API_KEY?: string;
  OPENAI_MODEL?: string;
}

export class SFWContainer extends DurableObject<Env> {
  private starting: Promise<void> | undefined;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    if (ctx.container?.running) {
      void ctx.blockConcurrencyWhile(() =>
        ctx.container!.setInactivityTimeout(INACTIVITY_TIMEOUT_MS),
      );
    }
  }

  async fetch(request: Request): Promise<Response> {
    try {
      this.starting ??= this.startAndWaitForPort().finally(() => {
        this.starting = undefined;
      });
      await this.starting;

      const url = new URL(request.url);
      url.protocol = "http:";
      url.host = "container";
      const forwarded = new Request(url, request);
      forwarded.headers.delete("host");

      // Fetcher forwarding preserves Streamlit's WebSocket upgrade requests.
      return await this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
    } catch (error) {
      console.error("SFW container is not ready:", error);
      return new Response(
        "Science Fair Winner is starting or temporarily unavailable. Please retry shortly.",
        { status: 503, headers: { "content-type": "text/plain; charset=utf-8", "retry-after": "10" } },
      );
    }
  }

  private async startAndWaitForPort(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      const env: Record<string, string> = {
        SFW_REQUIRE_R2: "true",
      };

      const optionalValues: Record<string, string | undefined> = {
        R2_ACCOUNT_ID: this.env.R2_ACCOUNT_ID,
        R2_BUCKET_NAME: this.env.R2_BUCKET_NAME,
        AWS_ACCESS_KEY_ID: this.env.AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY: this.env.AWS_SECRET_ACCESS_KEY,
        SFW_AI_PROVIDER: this.env.SFW_AI_PROVIDER,
        ANTHROPIC_API_KEY: this.env.ANTHROPIC_API_KEY,
        ANTHROPIC_MODEL: this.env.ANTHROPIC_MODEL,
        OPENAI_API_KEY: this.env.OPENAI_API_KEY,
        OPENAI_MODEL: this.env.OPENAI_MODEL,
      };

      for (const [key, value] of Object.entries(optionalValues)) {
        if (value) env[key] = value;
      }

      await container.start({
        image: container.images.base,
        instance: "standard-1",
        enableInternet: true,
        env,
      });
    }

    await container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS);
    const health = container.getTcpPort(PORT);

    // Streamlit exposes this endpoint once its HTTP and WebSocket server is ready.
    for (let attempt = 0; attempt < 90; attempt++) {
      try {
        const response = await health.fetch("http://container/_stcore/health");
        if (response.ok) return;
      } catch {
        // The application is still booting; retry below.
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    throw new Error("Timed out waiting for Streamlit on port 8501.");
  }
}

export default {
  fetch(request: Request, env: Env): Promise<Response> {
    return env.SFW_CONTAINER.getByName("sfw-production").fetch(request);
  },
} satisfies ExportedHandler<Env>;
