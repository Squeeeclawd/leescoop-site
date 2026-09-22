#!/usr/bin/env python3
"""Bounded public-source reader; never runs models, page code or publishing commands."""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser

from publishing_workflow import save, load_json

ROOT = Path(__file__).resolve().parents[1]
AGENT = 'LeeScoopDiscovery/1.0 (+https://leescoop.com)'


def public_url(url, allowed):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443) or p.fragment:
        raise ValueError('only credential-free public HTTPS URLs on port 443 are allowed')
    host = p.hostname.lower()
    if host.removeprefix('www.') not in allowed or host.endswith(('.local', '.localhost')):
        raise ValueError('source hostname is outside the bounded registry')
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        raise ValueError('IP-literal source URLs are not allowed')
    return p


def public_addresses(host):
    addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError('source DNS contains non-public addresses')
    return addresses


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, timeout):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.ip = ip

    def connect(self):
        raw = socket.create_connection((self.ip, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


class TextReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignore = 0
        self.parts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.ignore += 1
        if not self.ignore:
            if tag in ('p', 'div', 'h1', 'h2', 'h3', 'li', 'br', 'tr'):
                self.parts.append('\n')
            if tag == 'a':
                href = dict(attrs).get('href')
                if href:
                    self.links.append(href)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.ignore:
            self.ignore -= 1

    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data)


def remaining_delay(last_started, now, spacing):
    if last_started is None:
        return 0
    if now < last_started:
        raise ValueError('clock moved backwards; defer source access')
    return max(0, last_started + spacing - now)


def allowed_hosts(config):
    hosts = set()
    for source in config['sources']:
        if source.get('lane') == 'nearby' and not config.get('nearbyEnabled'):
            continue
        hosts.add(urlsplit(source['url']).hostname.lower().removeprefix('www.'))
        hosts.update(h.lower().removeprefix('www.') for h in source.get('articleHosts', []))
    return hosts


def request(url, *, state, run, config, journal, robots=False):
    parsed = public_url(url, allowed_hosts(config))
    host = parsed.hostname.lower().removeprefix('www.')
    network = config['network']
    requests = journal.setdefault('requests', [])
    if len(requests) >= min(24, network['maxPagesPerRun']):
        raise ValueError('run request cap reached (robots and redirects count)')
    if sum(x['host'] == host for x in requests) >= min(3, network['maxPagesPerHost']):
        raise ValueError('host request cap reached (robots and redirects count)')
    hosts_path = state / 'source-access' / 'hosts.json'
    hosts = load_json(hosts_path) if hosts_path.exists() else {}
    info = hosts.get(host, {})
    now = time.time()
    if info.get('deferUntil', 0) > now or any(r['host'] == host and r.get('status') in (401, 403, 406, 429) for r in requests):
        raise ValueError('source access deferred; no same-run access-failure retry')
    spacing = max(5, network['minSecondsPerHost'], info.get('robotsDelay', 0))
    delay = remaining_delay(info.get('startedEpoch'), now, spacing)
    if delay > 60:
        raise ValueError('source pacing requires more than 60 seconds; defer this source')
    if delay:
        time.sleep(delay)  # Bounded network rate limiting, not a reminder/polling timer.
    addresses = public_addresses(parsed.hostname)
    started = time.time()
    record = {'url': url, 'host': host, 'startedEpoch': started, 'fetchedAt': datetime.fromtimestamp(started, timezone.utc).isoformat(), 'robots': robots, 'status': 'pending'}
    requests.append(record)
    hosts[host] = {**info, 'startedEpoch': started}
    save(hosts_path, hosts)
    save(state / 'source-access' / 'runs' / f'{run}.json', journal)
    conn = PinnedHTTPS(parsed.hostname, addresses[0], min(20, network['timeoutSeconds']))
    try:
        target = parsed.path or '/'
        if parsed.query:
            target += '?' + parsed.query
        conn.request('GET', target, headers={'User-Agent': AGENT, 'Accept': 'text/html,application/xhtml+xml,text/plain,application/json', 'Accept-Encoding': 'identity'})
        response = conn.getresponse()
        headers = {k.lower(): v for k, v in response.getheaders()}
        record['status'] = response.status
        limit = min(2000000, network['maxResponseBytes'])
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError('response exceeds byte budget')
        if headers.get('content-encoding', 'identity') != 'identity':
            raise ValueError('unexpected compressed response; no unbounded decompression')
        record.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        if response.status in (401, 403, 406, 429) or response.status >= 500:
            defer = started + 86400
            if response.status == 429 and headers.get('retry-after'):
                value = headers['retry-after']
                try:
                    requested = started + int(value) if value.isdigit() else parsedate_to_datetime(value).timestamp()
                    defer = max(defer, requested)
                except (ValueError, TypeError, OverflowError):
                    pass
            hosts[host]['deferUntil'] = defer
        return response.status, headers, body, record
    except Exception as exc:
        record['error'] = str(exc)
        raise
    finally:
        conn.close()
        record['completedAt'] = datetime.now(timezone.utc).isoformat()
        save(hosts_path, hosts)
        save(state / 'source-access' / 'runs' / f'{run}.json', journal)


def check_robots(url, state, run, config, journal):
    parsed = public_url(url, allowed_hosts(config))
    origin = f'https://{parsed.hostname}'
    path = state / 'source-access' / 'robots' / (hashlib.sha256(origin.encode()).hexdigest() + '.json')
    cached = load_json(path) if path.exists() else None
    now = time.time()
    if not cached or not 0 <= now - cached['checkedEpoch'] < 86400:
        status, headers, body, record = request(origin + '/robots.txt', state=state, run=run, config=config, journal=journal, robots=True)
        if status not in (200, 404, 410):
            raise ValueError(f'robots unavailable (HTTP {status}); fail closed, no redirect/access bypass')
        text = body.decode('utf-8', errors='replace') if status == 200 else ''
        cached = {'checkedEpoch': time.time(), 'status': status, 'text': text, 'sha256': hashlib.sha256(body).hexdigest(), 'receipt': record}
        save(path, cached)
    parser = RobotFileParser(origin + '/robots.txt')
    parser.parse(cached['text'].splitlines())
    if not parser.can_fetch(AGENT, url):
        raise ValueError('robots disallows this source path')
    delay = parser.crawl_delay(AGENT) or parser.crawl_delay('*') or 0
    rate = parser.request_rate(AGENT) or parser.request_rate('*')
    if rate:
        delay = max(delay, rate.seconds / rate.requests)
    hosts_path = state / 'source-access' / 'hosts.json'
    hosts = load_json(hosts_path) if hosts_path.exists() else {}
    host = parsed.hostname.lower().removeprefix('www.')
    hosts.setdefault(host, {})['robotsDelay'] = delay
    save(hosts_path, hosts)
    return {'status': cached['status'], 'sha256': cached['sha256'], 'cachePath': str(path), 'checkedEpoch': cached['checkedEpoch']}


def fetch(url, state, run, config):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run):
        raise ValueError('unsafe run id')
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'source-fetch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another source request owns the lock; defer, do not fetch directly') from None
        journal_path = state / 'source-access' / 'runs' / f'{run}.json'
        journal = load_json(journal_path) if journal_path.exists() else {'schema': 'leescoop.source.requests.v1', 'run': run, 'requests': []}
        for hop in range(4):
            robots = check_robots(url, state, run, config, journal)
            status, headers, body, record = request(url, state=state, run=run, config=config, journal=journal)
            if status in (301, 302, 303, 307, 308):
                if not headers.get('location'):
                    raise ValueError('redirect has no location')
                url = urljoin(url, headers['location'])
                public_url(url, allowed_hosts(config))
                continue
            if status != 200:
                raise ValueError(f'source returned HTTP {status}; no bypass')
            mime = headers.get('content-type', '').split(';')[0].lower()
            if mime not in ('text/html', 'application/xhtml+xml', 'text/plain', 'application/json', 'text/calendar'):
                raise ValueError('source response is not a supported text document')
            key = hashlib.sha256((url + record['fetchedAt']).encode()).hexdigest()[:24]
            directory = state / 'source-access' / 'documents'
            directory.mkdir(parents=True, exist_ok=True)
            raw = directory / f'{key}.body'
            with raw.open('xb') as handle:
                handle.write(body)
            text = body.decode('utf-8', errors='replace')
            reader = TextReader()
            reader.feed(text if 'html' in mime else '')
            extracted = '\n'.join(line.strip() for line in ''.join(reader.parts).splitlines() if line.strip()) if 'html' in mime else text
            links = list(dict.fromkeys(urljoin(url, link) for link in reader.links))
            text_path = directory / f'{key}.txt'
            with text_path.open('x') as handle:
                handle.write(extracted)
            receipt = {'schema': 'leescoop.source.document.v1', 'run': run, 'url': url, 'httpStatus': status, 'fetchedAt': record['fetchedAt'], 'rawPath': str(raw), 'rawSha256': record['sha256'], 'textPath': str(text_path), 'textSha256': hashlib.sha256(extracted.encode()).hexdigest(), 'robots': robots, 'requestJournal': str(journal_path), 'links': links, 'excerpt': extracted[:12000], 'truncated': len(extracted)>12000}
            save(directory / f'{key}.json', receipt)
            return receipt
        raise ValueError('redirect limit exceeded')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=ROOT / 'docs/workflow/sources.json')
    parser.add_argument('--run', required=True)
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    try:
        result = fetch(args.url, args.state, args.run, load_json(args.config))
    except (OSError, ValueError, TypeError, KeyError, http.client.HTTPException) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
