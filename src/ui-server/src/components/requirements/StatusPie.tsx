import { useRef, useEffect } from 'react';

interface StatusPieProps {
  passCount: number;
  failCount: number;
}

export function StatusPie({ passCount, failCount }: StatusPieProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const total = passCount + failCount;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const size = 80;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
    ctx.scale(dpr, dpr);

    const cx = size / 2, cy = size / 2, r = 32, lw = 10;
    ctx.clearRect(0, 0, size, size);

    const style = getComputedStyle(document.documentElement);
    const errorColor = style.getPropertyValue('--error').trim() || '#f38ba8';
    const successColor = style.getPropertyValue('--success').trim() || '#a6e3a1';
    const textColor = style.getPropertyValue('--text-primary').trim() || '#cdd6f4';

    if (failCount > 0) {
      const failAngle = (failCount / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + failAngle);
      ctx.strokeStyle = errorColor;
      ctx.lineWidth = lw;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    if (passCount > 0) {
      const failAngle = (failCount / total) * Math.PI * 2;
      const passAngle = (passCount / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, -Math.PI / 2 + failAngle, -Math.PI / 2 + failAngle + passAngle);
      ctx.strokeStyle = successColor;
      ctx.lineWidth = lw;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    ctx.fillStyle = textColor;
    ctx.font = 'bold 16px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${passCount}/${total}`, cx, cy);
  }, [passCount, failCount, total]);

  return <canvas ref={canvasRef} />;
}
