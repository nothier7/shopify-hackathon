import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Wand2, ArrowRight, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Image } from '@/components/ui/image';
import StyleProfileBar from '@/components/StyleProfileBar';
import { useSession } from '@/lib/SessionContext';
import { base44 } from '@/api/base44Client';

const ITERATIONS = [
  { label: 'More cozy', direction: 'more cozy' },
  { label: 'More minimal', direction: 'more minimal' },
  { label: 'More colorful', direction: 'more colorful' },
  { label: 'More luxurious', direction: 'more luxurious' },
  { label: 'More affordable', direction: 'more affordable' },
  { label: 'More functional', direction: 'more functional' }
];

export default function FinalLook() {
  const navigate = useNavigate();
  const { designs, session, finalLook, saveFinalLook, updateFinalLook } = useSession();
  const [loading, setLoading] = useState(true);
  const [iterating, setIterating] = useState(false);
  const computedRef = useRef(false);

  useEffect(() => {
    if (designs.length === 0) {
      navigate('/');
      return;
    }
    if (finalLook?.final_look_url) {
      setLoading(false);
      return;
    }
    if (computedRef.current) return;
    computedRef.current = true;

    const compute = async () => {
      const liked = designs.filter(d => d.swipe_result === 'like');
      const passed = designs.filter(d => d.swipe_result === 'pass');

      const response = await base44.functions.invoke('computeFinalLook', {
        questionnaire: session,
        liked_designs: liked.map(d => ({
          style_name: d.style_name,
          description: d.description,
          style_metadata: d.style_metadata
        })),
        passed_designs: passed.map(d => ({
          style_name: d.style_name,
          description: d.description
        }))
      });

      const imageRes = await base44.functions.invoke('generateRoomImage', {
        prompt: response.data.final_look_prompt,
        reference_image_url: session?.photo_url
      });

      await saveFinalLook({
        ...response.data,
        final_look_url: imageRes.data.url
      });
      setLoading(false);
    };
    compute();
  }, []);

  const handleIterate = async (direction) => {
    if (iterating) return;
    setIterating(true);
    try {
      const response = await base44.functions.invoke('iterateFinalLook', {
        current_prompt: finalLook.final_look_prompt,
        current_description: finalLook.final_look_description,
        direction,
        questionnaire: session
      });
      const imageRes = await base44.functions.invoke('generateRoomImage', {
        prompt: response.data.final_look_prompt,
        reference_image_url: session?.photo_url
      });
      updateFinalLook({
        final_look_description: response.data.final_look_description,
        final_look_prompt: response.data.final_look_prompt,
        final_look_url: imageRes.data.url
      });
    } catch (err) {
      console.error(err);
    }
    setIterating(false);
  };

  if (designs.length === 0) return null;

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center px-6">
        <div className="w-10 h-10 rounded-full border border-foreground/20 border-t-foreground animate-spin mb-8" />
        <p className="font-display text-2xl mb-2">Creating your personalized room</p>
        <p className="text-muted-foreground font-light">Analyzing your swipes and designing the perfect room…</p>
      </div>
    );
  }

  const profile = finalLook?.style_profile || {};

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-12">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="text-center mb-8">
          <div className="text-xs uppercase tracking-widest text-muted-foreground mb-4">Your Dream Room</div>
          <h1 className="font-display text-3xl sm:text-4xl mb-3">Your final <span className="italic">look</span></h1>
          <p className="text-muted-foreground max-w-xl mx-auto font-light leading-relaxed">{finalLook?.final_look_description}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="relative rounded overflow-hidden border border-border aspect-[4/3] bg-secondary">
            {iterating ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-secondary">
                <RotateCw className="w-8 h-8 text-foreground mb-3 animate-spin" strokeWidth={1.5} />
                <p className="text-sm text-muted-foreground font-light">Redesigning your room…</p>
              </div>
            ) : (
              <Image src={finalLook?.final_look_url} fittingType="fill" className="w-full h-full" />
            )}
          </div>

          <div className="flex flex-col justify-center">
            <h3 className="text-xs uppercase tracking-widest text-muted-foreground mb-6">Your style profile</h3>
            <div className="space-y-4">
              {Object.entries(profile).map(([key, value], i) => (
                <StyleProfileBar key={key} label={key} value={value} delay={i * 100} />
              ))}
            </div>
          </div>
        </div>

        <div className="mb-8">
          <h3 className="font-display text-lg mb-3 flex items-center gap-2">
            <Wand2 className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} /> Want to tweak it?
          </h3>
          <div className="flex flex-wrap gap-2">
            {ITERATIONS.map(iter => (
              <Button
                key={iter.label}
                variant="outline"
                size="sm"
                onClick={() => handleIterate(iter.direction)}
                disabled={iterating}
                className="rounded-full border-foreground/30 text-foreground hover:bg-foreground/10 hover:border-foreground font-normal"
              >
                {iter.label}
              </Button>
            ))}
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
          <p className="text-sm text-muted-foreground mt-3 font-light">Find real products that bring this design to life</p>
        </div>
      </motion.div>
    </div>
  );
}