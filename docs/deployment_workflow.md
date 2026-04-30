# LeeScoop deployment workflow

## Public target
- Canonical domain: `https://leescoop.com`

## Cloudflare Pages settings
- Production branch: `main`
- Build command: `npm run build`
- Output directory: `dist`

## Publish flow
1. Work locally in `/home/shmee/Desktop/leescoop`.
2. Run `npm run build`.
3. Commit to `main`.
4. Push to `https://github.com/Squeeeclawd/leescoop-site.git`.
5. Let Cloudflare Pages build and deploy.
6. Verify the live route on `https://leescoop.com` once DNS/Pages wiring exists.
