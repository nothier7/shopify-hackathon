import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { X, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import SwipeCard from '@/components/SwipeCard';
import { useSession } from '@/lib/SessionContext';

export default function Swipe() {
  const navigate = useNavigate();
  const { designs, swipeDesign } = useSession();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [buttonSwipe, setButtonSwipe] = useState(null);
  const [exiting, setExiting] = useState(false);
  const [currentComment, setCurrentComment] = useState('');

  useEffect(() => {
    if (designs.length === 0) {
      navigate('/');
    }
  }, [designs.length, navigate]);

  const handleSwipe = async (result) => {
    if (exiting) return;
    setExiting(true);
    const design = designs[currentIndex];
    await swipeDesign(design.id, result, currentComment);
    setCurrentComment('');
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

      <Textarea
        value={currentComment}
        onChange={(event) => setCurrentComment(event.target.value)}
        placeholder="Optional: tell us what influenced this choice"
        maxLength={500}
        className="mb-5 min-h-20 resize-none bg-card"
      />

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
