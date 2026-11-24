// Layout points on a north-up, schematic map of Lee County. These represent
// communities, not municipal boundaries, venues or driving destinations.
export const communities = [
  { name: 'Boca Grande', x: 86, y: 76, dx: 14, dy: -13 },
  { name: 'Pine Island / Matlacha', x: 197, y: 208, dx: -11, dy: -17 },
  { name: 'Cape Coral', x: 333, y: 226, dx: -8, dy: 29 },
  { name: 'North Fort Myers', x: 405, y: 144, dx: -9, dy: -17 },
  { name: 'Fort Myers', x: 429, y: 182, dx: 14, dy: 15 },
  { name: 'Lehigh Acres', x: 610, y: 196, dx: 0, dy: 30 },
  { name: 'Captiva', x: 138, y: 290, dx: -2, dy: 28 },
  { name: 'Sanibel', x: 222, y: 352, dx: 0, dy: 29 },
  { name: 'Fort Myers Beach', x: 335, y: 353, dx: 0, dy: 47 },
  { name: 'Estero', x: 461, y: 357, dx: 17, dy: 5 },
  { name: 'Bonita Springs', x: 483, y: 442, dx: 13, dy: 12 }
];

export function areaId(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-$/, '');
}

export function columnShape(count: number, max: number) {
  const h = max > 0 ? 45 * count / max : 0;
  // Parallel projection: identical ground footprints, linear height scale.
  return {
    left: `M-8 -4L0 0V${-h}L-8 ${-h - 4}Z`,
    right: `M0 0L8 -4V${-h - 4}L0 ${-h}Z`,
    top: `M-8 ${-h - 4}l8 -4 8 4 -8 4Z`
  };
}
