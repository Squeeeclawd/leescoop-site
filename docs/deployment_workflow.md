# LeeScoop deployment workflow

## Public target
- Canonical domain: `https://leescoop.com`

## Cloudflare Pages settings
- Production branch: `main`
- Build command: `npm run build`
- Output directory: `dist`

## Automated publish flow
Use the isolated checkout, durable state, fixed quality/commit/push commands and live
receipt schema in `docs/command_contract.md`. The workflow stages only checkpoint
articles and selected covers, rejects unrelated dirt, and requires a fast-forward from
the inspected production base.

After Cloudflare Pages deploys, verify every released route on `https://leescoop.com`:
HTTP 200 with the expected title and direct source link, plus a cover response whose
bytes decode and hash to the checkpoint asset (not an HTML fallback). Parent records
the exact production commit and deployment reference. Only `finalize` may mark the
ledger published; push acceptance alone never does.
