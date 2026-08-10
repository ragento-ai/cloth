# Vercel Deployment

This repo is prepared to deploy as a Vercel Python/Flask project named `studio`.

## What is already configured

- `vercel.json` rewrites all routes to `server.py`
- `server.py` exposes the Flask `app` Vercel can run
- `config.py` automatically switches runtime-writable data to `/tmp/ragento-studio` when `VERCEL=1`
- `.vercelignore` excludes local creds, generated outputs, and bulky local-only assets from deployment
- `.python-version` pins Python `3.13`

## Required Vercel environment variables

Set these in the Vercel project before production deploy:

- `VERTEX_PROJECT_ID`
- `VERTEX_LOCATION`
- `VERTEX_CREDENTIALS_BASE64`

`VERTEX_CREDENTIALS_BASE64` should be the base64-encoded contents of your Vertex service account JSON.

Example:

```bash
base64 -w 0 vertex-cred.json
```

## Create and deploy the `studio` project

If you are already logged into the Vercel CLI:

```bash
./deploy-vercel.sh
```

Or run the steps manually:

```bash
vercel login
vercel project add studio
vercel link --project studio
vercel env add VERTEX_PROJECT_ID
vercel env add VERTEX_LOCATION
vercel env add VERTEX_CREDENTIALS_BASE64
vercel --prod
```

## Important runtime note

This app still stores uploaded SKU images, moodboards, and generated outputs on the local filesystem. In this Vercel setup, those runtime files are redirected away from the code directory into a writable temp area so the function can run, but they are not a durable asset store. For production persistence, move uploads and generated outputs to object storage such as Vercel Blob or S3.
