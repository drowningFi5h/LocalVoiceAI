import { useEffect, useRef } from 'react';

/** A perspective-projected torus, drawn locally without a WebGL dependency. */
export default function Resonance({ paused, energy }: { paused: boolean; energy: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const level = useRef(energy);
  const pointer = useRef({ x: 0, y: 0 });
  const phase = useRef(0);
  level.current = energy;

  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const ctx = el.getContext('2d');
    if (!ctx) return;
    let frame = 0, last = 0, visible = true, width = 0, height = 0;
    let tiltX = 0, tiltY = 0;
    const rings = Array.from({ length: 64 }, (_, i) => {
      const u = i / 64 * Math.PI * 2;
      return Array.from({ length: 65 }, (_, j) => {
        const v = j / 64 * Math.PI * 2;
        const radius = 1.43 + .57 * Math.cos(v);
        return [radius * Math.cos(u), radius * Math.sin(u), .57 * Math.sin(v)];
      });
    });
    function render(now: number) {
      frame = 0;
      if (!visible || document.hidden) return;
      if (!paused && now - last < 33) { frame = requestAnimationFrame(render); return; }
      const elapsed = last ? Math.min(now - last, 50) : 0;
      last = now;
      if (!paused) phase.current += elapsed * .000065;
      tiltX += ((paused ? 0 : pointer.current.y * .18) - tiltX) * .07;
      tiltY += ((paused ? 0 : pointer.current.x * .3) - tiltY) * .07;
      const ax = .83 + tiltX, ay = -.42 + tiltY + Math.sin(phase.current) * .24;
      const az = -.45 + (paused ? 0 : Math.sin(phase.current * .6) * .09);
      const scale = Math.min(width, height) * .205 * (1 + Math.min(level.current * 2, .08));
      const project = ([x, y, z]: number[]) => {
        const y1 = y * Math.cos(ax) - z * Math.sin(ax), z1 = y * Math.sin(ax) + z * Math.cos(ax);
        const x2 = x * Math.cos(ay) + z1 * Math.sin(ay), z2 = -x * Math.sin(ay) + z1 * Math.cos(ay);
        const x3 = x2 * Math.cos(az) - y1 * Math.sin(az), y3 = x2 * Math.sin(az) + y1 * Math.cos(az);
        const perspective = 6 / (6 - z2);
        return [width / 2 + x3 * scale * perspective, height / 2 + y3 * scale * perspective, z2];
      };
      ctx!.clearRect(0, 0, width, height);
      const projected = rings.map(ring => ring.map(project)).sort((a, b) =>
        a.reduce((s, p) => s + p[2], 0) - b.reduce((s, p) => s + p[2], 0));
      for (const ring of projected) {
        const depth = ring.reduce((sum, p) => sum + p[2], 0) / ring.length;
        const light = Math.max(0, Math.min(1, (depth + 2) / 4));
        ctx!.beginPath();
        ring.forEach(([x, y], i) => i ? ctx!.lineTo(x, y) : ctx!.moveTo(x, y));
        ctx!.closePath();
        ctx!.fillStyle = `rgba(16, 23, 22, ${.13 + light * .18})`;
        ctx!.fill();
        ctx!.strokeStyle = `rgba(${150 + light * 100}, ${115 + light * 106}, ${80 + light * 99}, ${.32 + light * .55})`;
        ctx!.lineWidth = .6 + light * .55;
        ctx!.stroke();
      }
      if (!paused) frame = requestAnimationFrame(render);
    }
    function schedule() { if (!frame && visible && !document.hidden) frame = requestAnimationFrame(render); }
    const resize = new ResizeObserver(() => {
      const rect = el.getBoundingClientRect();
      width = rect.width; height = rect.height;
      const ratio = Math.min(devicePixelRatio || 1, 2);
      el.width = Math.round(width * ratio); el.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      schedule();
    });
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (!visible) { cancelAnimationFrame(frame); frame = 0; last = 0; }
      else schedule();
    });
    const onVisibility = () => {
      cancelAnimationFrame(frame); frame = 0; last = 0; schedule();
    };
    resize.observe(el); visibility.observe(el);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      cancelAnimationFrame(frame); resize.disconnect(); visibility.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [paused]);

  return <canvas ref={canvas} className="resonance-canvas" aria-hidden="true"
    onPointerMove={event => {
      const rect = event.currentTarget.getBoundingClientRect();
      pointer.current = { x: (event.clientX - rect.left) / rect.width * 2 - 1, y: (event.clientY - rect.top) / rect.height * 2 - 1 };
    }} onPointerLeave={() => { pointer.current = { x: 0, y: 0 }; }}/ >;
}
