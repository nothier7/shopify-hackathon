import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import SwipeCard from '@/components/SwipeCard';
import { useSession } from '@/lib/SessionContext';
import { base44 } from '@/api/base44Client';

export default function Swipe() {
  const navigate = useNavigate();
  const { designs, swipeDesign, session, updateDesignImage } = useSession();
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [buttonSwipe, setButtonSwipe] = useState(null);
  const [exiting, setExiting] = useState(false);
  const generatedRef = useRef(false);

  useEffect(() => {
    if (designs.length === 0) {
      navigate('/');
      return;
    }
    if (generatedRef.current) return;
    generatedRef.current = true;

    if (designs.every(d => d.image_url)) {
      setLoading(false);
      return;
    }

    const generateImages = async () => {
      const batchSize = 3;
      const initialDesigns = designs;
      for (let i = 0; i < initialDesigns.length; i += batchSize) {
        const batch = initialDesigns.slice(i, i + batchSize);
        await Promise.all(batch.map(async (design) => {
          if (design.image_url) return;
          try {
            const res = await base44.functions.invoke('generateRoomImage', {
              prompt: design.image_prompt,
              reference_image_url: session?.photo_url
            });
            updateDesignImage(design.id, res.data.url);
            await base44.entities.RoomDesign.update(design.id, { image_url: res.data.url });
          } catch (err) {
            console.error('Image generation failed for', design.id, err);
          }
        }));
        setLoadingProgress(Math.min(i + batchSize, initialDesigns.length));
      }
      setLoading(false);
    };
    generateImages();
  }, []);

  const handleSwipe = async (result) => {
    if (exiting) return;
    setExiting(true);
    const design = designs[currentIndex];
    await swipeDesign(design.id, result);
    setButtonSwipe(null);
    setTimeout(() => {
      if (currentIndex + 1 >= designs.length) {
        navigate('/final');
      } else {
        setCurrentIndex(prev => prev + 1);
        setExiting(false);
      }
    }, 300);
  };

  const handleButtonSwipe = (direction) => {
    if (buttonSwipe || exiting) return;
    setButtonSwipe(direction);
  };

  if (designs.length === 0) return null;

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center px-6">
        <div className="w-10 h-10 rounded-full border border-foreground/20 border-t-foreground animate-spin mb-8" />
        <p className="font-display text-2xl mb-2">Generating your room variations</p>
        <p className="text-muted-foreground mb-8 font-light">
          {loadingProgress > 0 ? `${loadingProgress} of ${designs.length} rooms ready` : 'Starting…'}
        </p>
        <div className="w-64 h-px bg-secondary overflow-hidden">
          <motion.div
            className="h-full bg-foreground"
            initial={{ width: '0%' }}
            animate={{ width: `${(loadingProgress / designs.length) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>
    );
  }

  const visibleCards = designs.slice(currentIndex, currentIndex + 3).reverse();
  const likedCount = designs.filter(d => d.swipe_result === 'like').length;

  return (
    <div className="max-w-md mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <div className="flex items-center justify-between mb-6">
        <div className="text-sm text-muted-foreground">
          <span className="text-foreground font-display text-lg">{currentIndex + 1}</span>
          <span className="mx-1">/</span>
          <span>{designs.length}</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm">
          <Heart className="w-3.5 h-3.5 text-foreground" strokeWidth={1.5} />
          <span className="text-foreground font-display">{likedCount}</span>
          <span className="text-muted-foreground">liked</span>
        </div>
      </div>

      <div className="relative w-full aspect-[3/4] mb-8">
        <AnimatePresence>
          {visibleCards.map((design, i) => {
            const isTop = i === visibleCards.length - 1;
            const offsetFromTop = visibleCards.length - 1 - i;
            return (
              <SwipeCard
                key={design.id}
                design={design}
                isTop={isTop}
                offsetFromTop={offsetFromTop}
                onSwipe={handleSwipe}
                buttonSwipe={isTop ? buttonSwipe : null}
              />
            );
          })}
        </AnimatePresence>
      </div>

      <div className="flex items-center justify-center gap-6">
        <Button
          variant="outline"
          size="lg"
          onClick={() => handleButtonSwipe('pass')}
          disabled={exiting}
          className="rounded-full w-14 h-14 p-0 border-foreground/30 hover:border-foreground hover:bg-foreground/10 hover:text-foreground"
        >
          <X className="w-5 h-5" strokeWidth={1.5} />
        </Button>
        <Button
          size="lg"
          onClick={() => handleButtonSwipe('like')}
          disabled={exiting}
          className="rounded-full w-14 h-14 p-0"
        >
          <Heart className="w-5 h-5" strokeWidth={1.5} />
        </Button>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-4 tracking-wider uppercase">
        Swipe right if you like it, left if you don't
      </p>
    </div>
  );
}