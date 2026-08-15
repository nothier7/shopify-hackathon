import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import ProgressSteps from './ProgressSteps';
import FloatingFurniture from './FloatingFurniture';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();

  const pathToStep = {
    '/questionnaire': 1,
    '/upload': 2,
    '/swipe': 3,
    '/final': 4,
    '/products': 5
  };
  const currentStep = pathToStep[location.pathname] || 1;

  return (
    <div className="min-h-screen bg-background flex flex-col relative">
      <FloatingFurniture />
      <header className="border-b border-border bg-background/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <button onClick={() => navigate('/')} className="flex items-center group">
            <span className="font-display text-2xl tracking-tight text-accent group-hover:opacity-70 transition-opacity">roomly</span>
          </button>
          <ProgressSteps current={currentStep} />
        </div>
      </header>
      <main className="flex-1 relative z-10">
        <Outlet />
      </main>
    </div>
  );
}