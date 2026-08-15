import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const STEPS = ['Questions', 'Upload', 'Swipe', 'Final Look', 'Shop'];

export default function ProgressSteps({ current }) {
  return (
    <div className="flex items-center gap-1 sm:gap-2">
      {STEPS.map((step, i) => {
        const stepNum = i + 1;
        const isComplete = stepNum < current;
        const isCurrent = stepNum === current;
        return (
          <div key={step} className="flex items-center gap-1 sm:gap-2">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <div className={cn(
                "flex items-center justify-center w-6 h-6 sm:w-7 sm:h-7 rounded-full text-xs font-medium transition-all duration-300 border",
                isComplete && "border-foreground bg-foreground text-background",
                isCurrent && "border-foreground text-foreground",
                !isComplete && !isCurrent && "border-border text-muted-foreground"
              )}>
                {isComplete ? <Check className="w-3 h-3" strokeWidth={2.5} /> : stepNum}
              </div>
              <span className={cn(
                "text-xs hidden md:inline transition-colors",
                isCurrent ? "text-foreground" : "text-muted-foreground"
              )}>
                {step}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn(
                "w-3 sm:w-5 h-px transition-colors",
                stepNum < current ? "bg-foreground/40" : "bg-border"
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
}