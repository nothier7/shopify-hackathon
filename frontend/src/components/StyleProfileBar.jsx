import { useEffect, useState } from 'react';

export default function StyleProfileBar({ label, value, delay = 0 }) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setWidth(value * 100), delay + 100);
    return () => clearTimeout(timer);
  }, [value, delay]);

  const displayLabel = label.replace(/_/g, ' ');

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">{displayLabel}</span>
        <span className="text-xs tabular-nums text-foreground/80 font-medium">
          {Math.round(value * 100)}%
        </span>
      </div>
      <div className="h-1 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-foreground transition-all duration-1000 ease-out"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}