import { motion, useMotionValue, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Image } from '@/components/ui/image';

export default function SwipeCard({ design, onSwipe, isTop, offsetFromTop, buttonSwipe }) {
  const dragX = useMotionValue(0);
  const rotate = useTransform(dragX, [-200, 200], [-12, 12]);
  const likeOpacity = useTransform(dragX, [40, 120], [0, 1]);
  const passOpacity = useTransform(dragX, [-120, -40], [1, 0]);
  const [exitDir, setExitDir] = useState(0);

  const scale = 1 - offsetFromTop * 0.04;
  const yOffset = offsetFromTop * 10;
  const imageUrl = design.imageUrl || design.image_url;
  const designName = design.name || design.style_name;
  const description = design.description || design.items?.join(', ');

  useEffect(() => {
    if (!isTop || !buttonSwipe || exitDir !== 0) return;
    if (buttonSwipe === 'like') {
      setExitDir(1);
      onSwipe('like');
    } else if (buttonSwipe === 'pass') {
      setExitDir(-1);
      onSwipe('pass');
    }
  }, [buttonSwipe, isTop, exitDir]);

  const handleDragEnd = (event, info) => {
    if (info.offset.x > 100) {
      setExitDir(1);
      onSwipe('like');
    } else if (info.offset.x < -100) {
      setExitDir(-1);
      onSwipe('pass');
    } else {
      dragX.set(0);
    }
  };

  return (
    <motion.div
      drag={isTop && exitDir === 0 ? 'x' : false}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.8}
      onDrag={(e, info) => dragX.set(info.offset.x)}
      onDragEnd={handleDragEnd}
      style={{ rotate }}
      className="absolute inset-0"
      animate={
        exitDir !== 0
          ? { x: exitDir * 400, opacity: 0 }
          : { x: 0, scale, y: yOffset, opacity: 1 }
      }
      transition={
        exitDir !== 0
          ? { duration: 0.3, ease: 'easeOut' }
          : { type: 'spring', stiffness: 350, damping: 30 }
      }
    >
      <div className="relative w-full h-full rounded-lg overflow-hidden shadow-2xl bg-card border border-border">
        {imageUrl ? (
          <Image src={imageUrl} fittingType="fill" className="w-full h-full" />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-secondary">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-foreground/20 border-t-foreground rounded-full animate-spin" />
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Designing…</span>
            </div>
          </div>
        )}

        <motion.div
          style={{ opacity: likeOpacity }}
          className="absolute top-6 left-6 border border-foreground text-foreground text-lg font-display tracking-widest px-4 py-1.5 rounded-full rotate-[-18deg] z-10 bg-background/40 backdrop-blur-sm"
        >
          LIKE
        </motion.div>
        <motion.div
          style={{ opacity: passOpacity }}
          className="absolute top-6 right-6 border border-foreground text-foreground text-lg font-display tracking-widest px-4 py-1.5 rounded-full rotate-[18deg] z-10 bg-background/40 backdrop-blur-sm"
        >
          PASS
        </motion.div>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background/70 to-transparent p-6 pt-16 pointer-events-none">
          <h3 className="text-foreground font-display text-2xl mb-1">{designName}</h3>
          <p className="text-foreground/60 text-sm leading-relaxed">{description}</p>
        </div>
      </div>
    </motion.div>
  );
}
