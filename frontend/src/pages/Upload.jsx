import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UploadCloud, Check, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSession } from '@/lib/SessionContext';
import { generateDesigns } from '@/api/roomswipeClient';
import { cn } from '@/lib/utils';

export default function Upload() {
  const navigate = useNavigate();
  const { questionnaire, createSession, saveDesigns } = useSession();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!questionnaire) navigate('/questionnaire');
  }, []);

  useEffect(() => {
    if (!loading) {
      setElapsedSeconds(0);
      return undefined;
    }
    const started = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [loading]);

  if (!questionnaire) return null;

  const handleFile = (f) => {
    if (!f || !f.type.startsWith('image/')) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    handleFile(f);
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      setLoadingMessage('Designing room variations');
      const candidates = await generateDesigns(file, questionnaire);
      const session = await createSession(file, preview);
      await saveDesigns(candidates, session.id);
      navigate('/swipe');
    } catch (err) {
      console.error(err);
      setLoading(false);
      setLoadingMessage('');
      alert(err.message || 'Something went wrong. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center px-6">
        <div className="w-10 h-10 rounded-full border border-foreground/20 border-t-foreground animate-spin mb-8" />
        <p className="font-display text-xl mb-2">{loadingMessage}</p>
        <p className="text-sm text-muted-foreground font-light">
          Generating 10 designs in parallel · {elapsedSeconds}s elapsed
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="font-display text-3xl sm:text-4xl mb-2">Upload your <span className="italic">room</span></h1>
        <p className="text-muted-foreground mb-10 font-light">Drop a photo of your space and we'll generate personalized room variations.</p>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            'relative rounded border border-dashed transition-all duration-300 cursor-pointer overflow-hidden',
            dragging ? 'border-foreground bg-foreground/5' : 'border-foreground/20 hover:border-foreground/40 hover:bg-foreground/5',
            preview ? 'h-80' : 'h-64'
          )}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {preview ? (
            <div className="relative w-full h-full">
              <img src={preview} alt="Your room" className="w-full h-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-background/60 to-transparent" />
              <div className="absolute bottom-4 left-4 text-foreground text-sm flex items-center gap-2 font-light">
                <Check className="w-4 h-4" strokeWidth={2} />
                {file?.name || 'Your room photo'}
              </div>
              <div className="absolute top-4 right-4">
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); setPreview(null); }}
                  className="px-3 py-1.5 rounded-full border border-foreground/40 bg-background/60 backdrop-blur-sm text-foreground text-xs tracking-wider uppercase hover:bg-foreground/10 transition-colors"
                >
                  Change
                </button>
              </div>
            </div>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-6">
              <div className="w-12 h-12 rounded-full border border-foreground/30 flex items-center justify-center mb-4">
                <UploadCloud className="w-5 h-5 text-foreground" strokeWidth={1.5} />
              </div>
              <p className="font-display text-lg mb-1">Drop your room photo here</p>
              <p className="text-sm text-muted-foreground font-light">or click to browse — JPG, PNG up to 10MB</p>
            </div>
          )}
        </div>

        <Button
          variant="outline"
          onClick={handleGenerate}
          disabled={!file}
          size="lg"
          className="w-full mt-6 rounded-full tracking-widest uppercase text-sm font-normal h-14 group"
        >
          <Sparkles className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Generate Rooms
        </Button>
      </motion.div>
    </div>
  );
}
