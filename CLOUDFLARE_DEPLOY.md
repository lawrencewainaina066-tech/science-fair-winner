# Deploy SFW on Cloudflare

This deployment runs the existing Streamlit application in a Cloudflare Container, with a Worker forwarding HTTP and WebSocket traffic. It uses Cloudflare R2 for the saved project library because Container disks are ephemeral.

Target URL: https://sfw.wfw.co.ke

## Requirements

- A Cloudflare account with the `wfw.co.ke` zone active in that same account.
- Workers Paid plan. Cloudflare Containers are available on Workers Paid; the plan starts at US$5/month and usage beyond included allowances can add charges.
- A Cloudflare R2 bucket and an R2 API token scoped to that bucket with Object Read and Write.
- Access to the GitHub repository: https://github.com/lawrencewainaina066-tech/science-fair-winner

## 1. Create persistent project storage

1. In Cloudflare Dashboard, open **R2 Object Storage**.
2. Create a bucket named `sfw-projects`.
3. Create an R2 API token with **Object Read & Write** permission scoped only to this bucket.
4. Keep the Access Key ID and Secret Access Key private.

The app's saved research plans are stored in `/mnt/r2/projects` inside the container. The startup script mounts the R2 bucket there before starting Streamlit. Do not remove the bucket or its credentials while the service is running.

## 2. Connect the GitHub repository to Workers Builds

1. Open **Workers & Pages** in the Cloudflare Dashboard.
2. Choose **Create application** / **Connect to Git** and authorize GitHub if prompted.
3. Select `lawrencewainaina066-tech/science-fair-winner`.
4. Use the repository root as the build root directory.
5. Set the production branch to `main`.
6. Set the deploy command to `npx wrangler deploy`. The repository's `package.json` supplies Wrangler.
7. Start the first deployment.

Wrangler builds `cloudflare/Dockerfile`, publishes the image to Cloudflare's container registry, and deploys the Worker. The first container provisioning can take several minutes.

## 3. Add Worker secrets

After the Worker has been created, open its **Settings → Variables and Secrets**. Add these as encrypted secrets:

| Secret | Value |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account ID shown in the dashboard |
| `R2_BUCKET_NAME` | `sfw-projects` |
| `AWS_ACCESS_KEY_ID` | Access Key ID from the bucket-scoped R2 token |
| `AWS_SECRET_ACCESS_KEY` | Secret Access Key from the bucket-scoped R2 token |

Optional AI configuration (only if you want the AI Science Assistant enabled):

| Secret | Value |
|---|---|
| `SFW_AI_PROVIDER` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `ANTHROPIC_MODEL` | A model available to your Anthropic account |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | A model available to your OpenAI account |

Add secrets in Cloudflare only. Never commit API keys or R2 credentials to GitHub. After adding or changing secrets, trigger a new deployment/restart so the Container receives the updated values.

The deployment deliberately requires R2 credentials at startup. This prevents SFW from silently saving research projects to a temporary container disk.

## 4. Attach the custom domain

The Wrangler configuration requests the custom domain `sfw.wfw.co.ke`. Cloudflare Custom Domains create the corresponding DNS record and TLS certificate automatically when the zone is active in the same account.

If Cloudflare reports that the hostname already has a DNS record, inspect the existing `sfw.wfw.co.ke` record before changing it. Remove or replace only that subdomain record if it is safe to do so. Do not change the root `wfw.co.ke` or `www.wfw.co.ke` records.

## 5. Verify the deployment

- Open https://sfw.wfw.co.ke and wait for the first container startup.
- Confirm the home page loads.
- Open the AI Science Assistant and verify its offline mode or configured provider.
- Create a sample research plan, save it, restart/redeploy the Worker, and confirm it remains in Project Library. This verifies R2 persistence.
- Test dataset upload, charts, DOCX/PDF exports, and the Streamlit WebSocket connection.
- Check **Workers & Pages → Containers** and Worker logs if the first request returns a temporary 503.

## Architecture and operational notes

- Cloudflare Worker: hostname routing and HTTP/WebSocket forwarding.
- Cloudflare Container: Python 3.11 + Streamlit + SFW application.
- Cloudflare R2: persistent saved research plans.
- The container uses a `standard-1` instance (0.5 vCPU, 4 GiB RAM, 8 GB disk). This is an initial baseline; measure real usage before increasing capacity.
- Container local disk is ephemeral. The project library is therefore mounted from R2 using TigrisFS/FUSE. FUSE-backed object storage is not equivalent to a local POSIX disk and may be slower; it is used here for small JSON project files.
- The Streamlit app is currently a single shared workspace. It does not yet implement user accounts, per-user project isolation, or role-based access. If the service is intended only for WFW staff, configure Cloudflare Access before sharing the URL.
- The AI features are optional and incur separate charges from the model provider.
- This is a deployment baseline, not a claim that the application has passed production load, security, or scientific validation testing.

## Local deployment commands

With Node.js, Docker Desktop (or another Docker-compatible engine), and Cloudflare account access installed/configured:

```bash
npm install
npx wrangler dev
npx wrangler deploy
npx wrangler containers list
```

For local testing of the R2 mount, FUSE support must be available in the local container engine. Do not use real production R2 credentials in an untrusted local environment.
