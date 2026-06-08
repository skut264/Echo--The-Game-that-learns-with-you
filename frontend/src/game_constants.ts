// Echo Frontend - Fibonacci/Golden Ratio constants for canvas rendering

export const PHI = 1.618033988749895;
export const GOLDEN_ANGLE = 137.50776405003785;

export const NOTE_COLORS: string[] = [
  '#e94560', '#0f3460', '#533483', '#ffd700',
  '#2ecc71', '#3498db', '#e8d5b7', '#ff6b6b',
];

export const BG_COLORS: Record<string, string> = {
  idle: '#1a1a2e',
  active: '#16213e',
  struggle: '#2b2d42',
  gap: '#3b3b4f',
  flow: '#e94560',
  gold: '#ffd700',
  coach: '#e8d5b7',
};

export const GOLDEN_CANVAS = {
  centerX: 0.382,
  centerY: 0.382,
  horizonY: 0.382,
  divider1: 0.236,
  divider2: 0.382,
  divider3: 0.618,
  divider4: 0.764,
};

export function goldenSpiralPoint(
  index: number,
  canvasW: number,
  canvasH: number,
  maxNotes: number,
): { x: number; y: number; size: number; rotation: number } {
  const angle = (index * GOLDEN_ANGLE * Math.PI) / 180;
  const cx = canvasW * GOLDEN_CANVAS.centerX;
  const cy = canvasH * GOLDEN_CANVAS.centerY;
  const maxR = Math.min(canvasW, canvasH) * 0.35;
  const radius = maxR * (1 - Math.pow(PHI, -index - 1));
  const jitter = 0.92 + Math.random() * 0.16;
  const x = cx + radius * Math.cos(angle) * jitter;
  const y = cy + radius * Math.sin(angle) * jitter;
  const size = Math.max(20, 48 / Math.pow(PHI, index / 2 + 1));
  const rotation = (angle * 180) / Math.PI % 360;
  return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, size: Math.round(size * 10) / 10, rotation: Math.round(rotation * 10) / 10 };
}

export function fibTiming(baseMs: number, difficulty: number, index: number = 0): number {
  return Math.max(80, Math.round(baseMs / (difficulty * Math.pow(PHI, -index + 1))));
}

// Generate a decorative fibonacci spiral SVG path data
export function fibSpiralPath(cx: number, cy: number, maxR: number, arms: number = 3, steps: number = 80): string {
  let path = '';
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * 6 * Math.PI;
    const r = maxR * (1 - Math.pow(PHI, -i / 10));
    const x = cx + r * Math.cos(t);
    const y = cy + r * Math.sin(t);
    path += i === 0 ? `M${x},${y}` : `L${x},${y}`;
  }
  return path;
}