function generateContinentDots(): [number, number, number][] {
  const zones = [
    { cx: 280, cy: 230, rx: 180, ry: 140, density: 0.55 },
    { cx: 480, cy: 110, rx: 60, ry: 60, density: 0.4 },
    { cx: 430, cy: 540, rx: 100, ry: 170, density: 0.5 },
    { cx: 820, cy: 220, rx: 90, ry: 80, density: 0.55 },
    { cx: 880, cy: 460, rx: 130, ry: 180, density: 0.55 },
    { cx: 980, cy: 320, rx: 70, ry: 70, density: 0.5 },
    { cx: 1150, cy: 250, rx: 220, ry: 130, density: 0.55 },
    { cx: 1080, cy: 360, rx: 70, ry: 70, density: 0.5 },
    { cx: 1280, cy: 440, rx: 90, ry: 60, density: 0.5 },
    { cx: 1400, cy: 580, rx: 110, ry: 70, density: 0.5 },
  ]
  const dots: [number, number, number][] = []
  let seed = 17
  const rand = () => {
    seed = (seed * 9301 + 49297) % 233280
    return seed / 233280
  }
  zones.forEach(z => {
    const count = Math.floor(z.rx * z.ry * 0.012 * z.density)
    for (let i = 0; i < count; i += 1) {
      const a = rand() * Math.PI * 2
      const r = Math.sqrt(rand())
      const x = z.cx + Math.cos(a) * r * z.rx + (rand() - 0.5) * 14
      const y = z.cy + Math.sin(a) * r * z.ry + (rand() - 0.5) * 14
      dots.push([x, y, 1.1 + rand() * 0.8])
    }
  })
  return dots
}

export const CONTINENT_DOTS = generateContinentDots()

// Market codes are ISO-3166 alpha-2 (plus the synthetic "GLOBAL" bucket).
// Coordinates are tuned to the existing 1600×780 world-map viewBox.
export const MARKET_LAYOUT: Record<string, { name: string; x: number; y: number; size: number }> = {
  // East / Southeast Asia (clustered around SG hub)
  SG: { name: '新加坡', x: 1240, y: 460, size: 18 },
  TH: { name: '泰国', x: 1168, y: 410, size: 15 },
  JP: { name: '日本', x: 1380, y: 280, size: 14 },
  KR: { name: '韩国', x: 1340, y: 295, size: 13 },
  ID: { name: '印尼', x: 1280, y: 525, size: 13 },
  MY: { name: '马来西亚', x: 1195, y: 470, size: 13 },
  VN: { name: '越南', x: 1228, y: 385, size: 13 },
  PH: { name: '菲律宾', x: 1335, y: 445, size: 13 },
  // Other regions
  US: { name: '美国', x: 320, y: 265, size: 16 },
  GLOBAL: { name: '全球', x: 800, y: 120, size: 14 },
}

/** UI display order: 全球 → 美国 → 发达国家 → 新兴市场 */
export const MARKET_DISPLAY_ORDER: readonly string[] = [
  'GLOBAL',
  'US',
  'JP', 'KR', 'SG',
  'TH', 'MY', 'ID', 'VN', 'PH',
]

export function compareMarketDisplayOrder(a: string, b: string): number {
  const ia = MARKET_DISPLAY_ORDER.indexOf(a)
  const ib = MARKET_DISPLAY_ORDER.indexOf(b)
  const rankA = ia === -1 ? MARKET_DISPLAY_ORDER.length + 1 : ia
  const rankB = ib === -1 ? MARKET_DISPLAY_ORDER.length + 1 : ib
  if (rankA !== rankB) return rankA - rankB
  return a.localeCompare(b)
}

export const DISTRICT_LAYOUT: Record<string, { x: number; y: number; sub: string }> = {
  orchard: { x: 540, y: 340, sub: 'Orchard' },
  marina: { x: 700, y: 425, sub: 'Marina Bay' },
  bugis: { x: 600, y: 270, sub: 'Bugis' },
  jurong: { x: 280, y: 360, sub: 'Jurong East' },
  tampines: { x: 830, y: 320, sub: 'Tampines' },
  changi: { x: 940, y: 295, sub: 'Changi' },
  cbd: { x: 620, y: 405, sub: 'CBD' },
}
