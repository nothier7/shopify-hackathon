import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSession } from '@/lib/SessionContext';
import FloatingFurniture from '@/components/FloatingFurniture';

const STEPS = [
  { title: 'Upload your room', desc: 'Snap a photo of your space and tell us your budget and goals.' },
  { title: 'Swipe through designs', desc: 'Like and pass on AI-generated rooms. We learn your taste.' },
  { title: 'Build your room', desc: 'Get a personalized final look with real products you can buy now.' }
];

export default function Home() {
  const navigate = useNavigate();
  const { reset } = useSession();

  const handleStart = () => {
    reset();
    navigate('/questionnaire');
  };

  return (
    <div className="min-h-screen bg-background">
      <section className="relative min-h-screen flex items-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-secondary" />
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-accent/15 rounded-full blur-3xl animate-float" />
        <FloatingFurniture />

        <div className="absolute right-4 sm:right-12 top-1/2 -translate-y-1/2 font-display text-[12rem] sm:text-[18rem] font-bold text-accent/10 select-none pointer-events-none leading-none">
          01
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-6">
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <div className="flex items-center mb-12 mt-24">
              <span className="font-display text-3xl tracking-tight text-accent">roomly</span>
            </div>

            <h1 className="font-display text-5xl sm:text-7xl lg:text-8xl leading-[1.05] mb-8 max-w-3xl">
              Don't shop for furniture.<br />
              <span className="italic font-light">Design your room.</span>
            </h1>

            <p className="text-base sm:text-lg text-muted-foreground mb-12 max-w-md leading-relaxed font-light">
              Upload a photo, swipe through AI-generated room designs, and discover real products that bring your dream space to life.
            </p>

            <Button variant="default" size="lg" onClick={handleStart} className="rounded-full px-10 h-14 text-sm tracking-widest uppercase font-normal group">
              Start Designing
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </motion.div>
        </div>
      </section>

      <section className="relative py-32 px-6 border-t border-border">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-display text-4xl sm:text-5xl font-light mb-20">
            How it <span className="italic">works</span>
          </h2>
          <div className="space-y-20">
            {STEPS.map((step, i) => (
              <div key={step.title} className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
                <div className="md:col-span-2 font-display text-5xl text-foreground/30">
                  0{i + 1}
                </div>
                <div className="md:col-span-4">
                  <h3 className="font-display text-xl">{step.title}</h3>
                </div>
                <div className="md:col-span-6">
                  <p className="text-muted-foreground leading-relaxed font-light">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}