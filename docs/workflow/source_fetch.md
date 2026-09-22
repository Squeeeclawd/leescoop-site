# Bounded source reads

Use the managed script from the current runtime checkout:

```sh
python3 scripts/publishing_source_fetch.py --state /home/shmee/.openclaw/workspace/state/leescoop-publishing --run <one-unique-discovery-or-review-run> --url 'https://registered-source.example/observed-detail-path/'
```

Keep one run ID for all source requests in a discovery/review run; never change it to evade a cap. Invoke serially. A held lock, access denial, robots failure or cap is a recorded gap, not permission to use curl, browser, web_fetch, another user-agent, or a direct HTTP fallback. Search snippets remain unverified leads; detail collection goes through this helper.

The helper takes a nonblocking global lock, validates all resolved addresses as public and pins the TLS connection to a checked address while retaining hostname/certificate verification. It checks registered-host redirects, robots and Crawl-delay/Request-rate, and enforces >=5 seconds between same-host request starts across runs. It permits <=24 actual requests/run and <=3/host, counting robots and redirect hops too; the limits may be lowered by config, not increased. Robots policies are cached for 24h. Event content is never reused as fresh evidence. It uses no cookies, credentials, browser state, script execution, proxy bypass or login.

401/403/406/429 and server failures defer the host conservatively; Retry-After can extend the deferral. Unknown robots status, unsupported text encoding/type, private DNS, oversized response or TLS failure blocks that read. The report must preserve these gaps. Network rate-limit waits are bounded to 60 seconds; longer waits defer instead of looping.

Source artifacts live under canonical `source-access/`: actual URL/timestamps/status/body hash in the request journal, robots evidence, raw response, extracted inert text, and observed links. The CLI prints a bounded excerpt and full local text path. Read full artifacts when needed; do not infer unseen text from truncation. These are observed source documents, not final event verification or permission to publish. The stronger reviewer still confirms date, title, location, access, practical details, duplication and editorial value.
