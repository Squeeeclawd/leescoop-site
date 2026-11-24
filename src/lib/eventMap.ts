// Only offer a map for a street address, not a city, venue name, or unspecified meeting point.
export function eventMapUrl(address?: string, city?: string): string | null {
  const street = address?.trim();
  if (!street || !/^\d+[a-z]?(?:-\d+)?\s+\S/i.test(street)) return null;

  const locality = city?.trim();
  const parts = [street];
  if (locality && !street.toLowerCase().includes(locality.toLowerCase())) parts.push(locality);
  if (!/\b(?:FL|Florida)\b/i.test(street)) parts.push('FL');

  const query = new URLSearchParams({ api: '1', query: parts.join(', ') });
  return `https://www.google.com/maps/search/?${query}`;
}
