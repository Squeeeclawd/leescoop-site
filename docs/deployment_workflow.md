# LeeScoop deployment workflow

## Public target
- Canonical domain: `https://leescoop.com`

## Cloudflare Pages settings
- Production branch: `main`
- Build command: `npm run build`
- Output directory: `dist`

## Publish flow
1. Work locally in `/home/shmee/Desktop/leescoop`.
2. Run `npm run validate`, `npm run check`, date/discovery tests, then `MALLOC_ARENA_MAX=2 UV_THREADPOOL_SIZE=2 NODE_OPTIONS=--max-old-space-size=2048 npm run build`.
3. Commit to `main`.
4. Push main using the existing origin SSH remote; stage explicit task paths only and exclude protected user files.
5. Let Cloudflare Pages build and deploy.
6. Verify every released route on `https://leescoop.com`: HTTP 200, expected title/source link, and expected cover reference. Verify cover responses decode as PNG 1216x704, not HTML. Check homepage date chips.
7. Record commit, URLs, test and HTTP evidence in the release note. A successful push is not completed publication. Keep ownership until production passes or report a concrete blocker. Rendered desktop/mobile verification remains unverified when browser navigation is policy-blocked; do not bypass that restriction.
