import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight, Bed, Sofa, UtensilsCrossed, Briefcase, Utensils, Bath, Baby, Trees, Home,
  Coffee, Gem, LayoutGrid, Wrench, Users, Sparkles, Circle, Layers, Scale, Shuffle,
  ShoppingBag, Hammer
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { useSession } from '@/lib/SessionContext';
import { cn } from '@/lib/utils';

const ROOM_TYPES = [
  { label: 'Bedroom', icon: Bed },
  { label: 'Living room', icon: Sofa },
  { label: 'Kitchen', icon: UtensilsCrossed },
  { label: 'Office', icon: Briefcase },
  { label: 'Dining room', icon: Utensils },
  { label: 'Bathroom', icon: Bath },
  { label: 'Nursery', icon: Baby },
  { label: 'Outdoor', icon: Trees },
  { label: 'Other', icon: Home },
];

const AGES = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+'];

const EFFORT_LEVELS = [
  { label: 'Just buy things', value: 'buy_only', icon: ShoppingBag },
  { label: 'Some rearranging / DIY', value: 'some_diy', icon: Hammer },
  { label: 'Major redesign', value: 'major_changes', icon: Wrench },
];

const GOALS = [
  { label: 'Cozy', icon: Coffee },
  { label: 'Expensive-looking', icon: Gem },
  { label: 'Organized', icon: LayoutGrid },
  { label: 'Functional', icon: Wrench },
  { label: 'Guest-ready', icon: Users },
  { label: 'Completely new vibe', icon: Sparkles },
];

const STYLE_PREFS = [
  { label: 'Minimalist', icon: Circle },
  { label: 'Maximalist', icon: Layers },
  { label: 'Somewhere in between', icon: Scale },
  { label: 'No preference', icon: Shuffle },
];

export default function Questionnaire() {
  const navigate = useNavigate();
  const { setQuestionnaire } = useSession();
  const [data, setData] = useState({
    room_type: '',
    budget: '$3,000',
    effort: '',
    age: '',
    goal: '',
    style_preferences: []
  });
  const [budgetMax, setBudgetMax] = useState(3000);

  const handleBudgetChange = (vals) => {
    setBudgetMax(vals[0]);
    setData(p => ({ ...p, budget: `$${vals[0].toLocaleString()}` }));
  };

  const handleBudgetInput = (e) => {
    const val = parseInt(e.target.value.replace(/[^0-9]/g, '')) || 0;
    const clamped = Math.min(Math.max(val, 0), 10000);
    setBudgetMax(clamped);
    setData(p => ({ ...p, budget: `$${clamped.toLocaleString()}` }));
  };

  const handleStylePref = (pref) => {
    setData(p => ({ ...p, style_preferences: [pref] }));
  };

  const canContinue = data.room_type && data.budget && data.effort && data.age && data.goal && data.style_preferences.length > 0;

  const handleContinue = () => {
    setQuestionnaire(data);
    navigate('/upload');
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="font-display text-3xl sm:text-4xl mb-2">Let's design your <span className="italic">room</span></h1>
        <p className="text-muted-foreground mb-10 font-light">Tell us about your space and we'll create personalized room designs for you.</p>

        <div className="space-y-10">
          {/* Question 1: Room Type */}
          <div>
            <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-4">What are you redesigning?</label>
            <div className="grid grid-cols-3 gap-3">
              {ROOM_TYPES.map(({ label, icon: Icon }) => {
                const selected = data.room_type === label;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setData(p => ({ ...p, room_type: label }))}
                    className={cn(
                      'flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-300 group',
                      selected
                        ? 'border-foreground bg-foreground/5 text-foreground'
                        : 'border-border bg-transparent text-muted-foreground hover:border-foreground/40 hover:text-foreground hover:bg-foreground/[0.02]'
                    )}
                  >
                    <Icon className="w-6 h-6 transition-transform group-hover:scale-110" strokeWidth={1.5} />
                    <span className="text-xs font-medium text-center leading-tight">{label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question 2: Budget */}
          <div>
            <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-4">What's your maximum budget?</label>
            <div className="p-6 rounded-xl border border-border bg-card">
              <div className="flex items-baseline gap-1 mb-6">
                <span className="font-display text-3xl text-muted-foreground">$</span>
                <input
                  type="text"
                  inputMode="numeric"
                  value={budgetMax.toLocaleString()}
                  onChange={handleBudgetInput}
                  className="font-display text-3xl bg-transparent border-b border-border focus:border-foreground outline-none w-40 transition-colors"
                />
              </div>
              <Slider
                value={[budgetMax]}
                onValueChange={handleBudgetChange}
                min={0}
                max={10000}
                step={100}
                className="py-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-3">
                <span>$0</span>
                <span>$10,000+</span>
              </div>
            </div>
          </div>

          {/* Question 3: Effort */}
          <div>
            <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-4">How much work are you willing to do?</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {EFFORT_LEVELS.map(({ label, value, icon: Icon }) => {
                const selected = data.effort === value;
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setData(p => ({ ...p, effort: value }))}
                    className={cn(
                      'flex items-center sm:flex-col sm:text-center gap-3 p-4 rounded-xl border transition-all duration-300',
                      selected
                        ? 'border-foreground bg-foreground/5 text-foreground'
                        : 'border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground'
                    )}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" strokeWidth={1.5} />
                    <span className="text-xs font-medium">{label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question 4: Age */}
          <div>
            <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-4">How old are you?</label>
            <div className="flex flex-wrap gap-2">
              {AGES.map(age => {
                const selected = data.age === age;
                return (
                  <button
                    key={age}
                    type="button"
                    onClick={() => setData(p => ({ ...p, age }))}
                    className={cn(
                      'px-5 py-2.5 rounded-full border text-sm font-medium transition-all duration-300',
                      selected
                        ? 'border-foreground bg-foreground text-background'
                        : 'border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground'
                    )}
                  >
                    {age}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question 5: Goals */}
          <div>
            <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-4">What's your main goal?</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {GOALS.map(({ label, icon: Icon }) => {
                const selected = data.goal === label;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setData(p => ({ ...p, goal: label }))}
                    className={cn(
                      'flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-300 group',
                      selected
                        ? 'border-foreground bg-foreground/5 text-foreground'
                        : 'border-border bg-transparent text-muted-foreground hover:border-foreground/40 hover:text-foreground hover:bg-foreground/[0.02]'
                    )}
                  >
                    <Icon className="w-5 h-5 transition-transform group-hover:scale-110" strokeWidth={1.5} />
                    <span className="text-xs font-medium text-center leading-tight">{label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Question 6: Style Preference */}
          <div>
            <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-4">Your aesthetic preference?</label>
            <div className="grid grid-cols-2 gap-3">
              {STYLE_PREFS.map(({ label, icon: Icon }) => {
                const selected = data.style_preferences[0] === label;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => handleStylePref(label)}
                    className={cn(
                      'flex items-center gap-3 p-4 rounded-xl border transition-all duration-300 group',
                      selected
                        ? 'border-foreground bg-foreground/5 text-foreground'
                        : 'border-border bg-transparent text-muted-foreground hover:border-foreground/40 hover:text-foreground hover:bg-foreground/[0.02]'
                    )}
                  >
                    <Icon className="w-5 h-5 transition-transform group-hover:scale-110 flex-shrink-0" strokeWidth={1.5} />
                    <span className="text-sm font-medium text-left leading-tight">{label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <Button
          variant="outline"
          onClick={handleContinue}
          disabled={!canContinue}
          size="lg"
          className="w-full mt-10 rounded-full tracking-widest uppercase text-sm font-normal h-14 group"
        >
          Continue
          <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
        </Button>
      </motion.div>
    </div>
  );
}
