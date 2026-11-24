// Browser URL and navigation events for the deterministic homepage DOM fixtures.
export function discoveryTestWindow(handlers, setInterval = () => {}) {
  const location = {href: 'https://leescoop.com/?ref=newsletter'};
  return {
    location,
    history: {replaceState(_state, _title, href) { location.href = href; }},
    addEventListener(name, handler) { handlers[name] = handler; },
    setInterval
  };
}
