import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Image } from '@/components/ui/image';
import StyleProfileBar from '@/components/StyleProfileBar';
import { useSession } from '@/lib/SessionContext';
import {
  finalizeRecommendation,
  generateFinalDesign,
  learnPreferences
} from '@/api/roomswipeApi';

export default function FinalLook() {
  const navigate = useNavigate();
  const {
    designs,
    swipes,
    photoFile,
    preferenceProfile,
    recommendedDesign,
    saveRecommendation,
    manifest,
    setManifest
  } = useSession();
  const [loading, setLoading] = useState(!manifest);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (designs.length !== 10 || swipes.length !== 10 || !photoFile) {
      navigate('/upload');
      return undefined;
    }
    if (manifest && recommendedDesign && preferenceProfile) {
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    const createFinalLook = async () => {
      setLoading(true);
      setError('');
      try {
        const [profile, finalization] = await Promise.all([
          learnPreferences(designs, swipes),
          finalizeRecommendation(designs, swipes)
        ]);
        const design = finalization.recommendedDesign;
        const finalManifest = await generateFinalDesign(photoFile, design);
        if (cancelled) return;
        saveRecommendation(profile, design);
        setManifest(finalManifest);
        setLoading(false);
      } catch (requestError) {
        if (cancelled) return;
        console.error(requestError);
        setError(requestError.message || 'We could not create your final room.');
        setLoading(false);
      }
    };

    createFinalLook();
    return () => {
      cancelled = true;
    };
  }, [
    attempt,
    designs,
    manifest,
    navigate,
    photoFile,
    preferenceProfile,
    recommendedDesign,
    saveRecommendation,
    setManifest,
    swipes
  ]);

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center px-6">
        <div className="w-10 h-10 rounded-full border border-foreground/20 border-t-foreground animate-spin mb-8" />
        <p className="font-display text-2xl mb-2">Creating your personalized room</p>
        <p className="text-muted-foreground font-light">Learning your taste and redesigning the original space…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <p className="font-display text-2xl mb-3">The final room needs another try</p>
        <p className="text-muted-foreground max-w-lg mb-6" role="alert">{error}</p>
        <Button variant="outline" onClick={() => setAttempt(value => value + 1)} className="rounded-full">
          <RotateCw className="w-4 h-4 mr-2" /> Retry final room
        </Button>
      </div>
    );
  }

  if (!manifest || !recommendedDesign || !preferenceProfile) return null;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-12">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="text-center mb-8">
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-4">
            {recommendedDesign.matchPercent}% match
          </div>
          <h1 className="font-display text-3xl sm:text-4xl mb-3">{recommendedDesign.name}</h1>
          <p className="text-muted-foreground max-w-xl mx-auto font-light leading-relaxed">
            {recommendedDesign.description}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="relative rounded overflow-hidden border border-border aspect-[4/3] bg-secondary">
            <Image src={manifest.finalImageUrl} fittingType="fill" className="w-full h-full" />
          </div>

          <div className="flex flex-col justify-center">
            <h3 className="text-xs uppercase tracking-widest text-muted-foreground mb-6">Your learned style profile</h3>
            <div className="space-y-4">
              {Object.entries(preferenceProfile.attributes).map(([key, value], index) => (
                <StyleProfileBar
                  key={key}
                  label={key}
                  value={Math.max(0, Math.min(1, (value + 1) / 2))}
                  delay={index * 100}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="text-center">
          <Button
            variant="outline"
            size="lg"
            onClick={() => navigate('/products')}
            className="group px-10 rounded-full tracking-widest uppercase text-sm font-normal h-14"
          >
            Build This Room
            <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>
          <p className="text-sm text-muted-foreground mt-3 font-light">
            Search live Shopify merchants for the items in this design
          </p>
        </div>
      </motion.div>
    </div>
  );
}
