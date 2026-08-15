import React, { createContext, useContext, useState, useCallback } from 'react';

const SessionContext = createContext(null);

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
}

function parseBudgetValue(budget) {
  if (!budget) return 1000;
  const numbers = budget.match(/[\d,]+/g);
  if (numbers && numbers.length >= 2) return parseInt(numbers[1].replace(/,/g, ''));
  if (numbers && numbers.length >= 1) return parseInt(numbers[0].replace(/,/g, ''));
  return 1000;
}

export function SessionProvider({ children }) {
  const [questionnaire, setQuestionnaire] = useState(null);
  const [session, setSession] = useState(null);
  const [designs, setDesigns] = useState([]);
  const [finalLook, setFinalLook] = useState(null);
  const [matchedProducts, setMatchedProducts] = useState([]);
  const [cart, setCart] = useState([]);

  const createSession = useCallback(async (photoFile, photoUrl) => {
    const s = {
      id: crypto.randomUUID(),
      ...questionnaire,
      photo_file: photoFile,
      photo_url: photoUrl,
      budget_value: parseBudgetValue(questionnaire.budget),
      status: 'swiping'
    };
    setSession(s);
    return s;
  }, [questionnaire]);

  const saveDesigns = useCallback(async (designConcepts, sessionId) => {
    const records = designConcepts.map((d, i) => ({
        session_id: sessionId,
        id: d.id,
        style_name: d.name,
        description: `${d.lighting}; ${d.items.join(', ')}`,
        image_url: d.imageUrl,
        style_metadata: d.attributes,
        api_candidate: d,
        swipe_result: 'pending',
        swipe_comment: '',
        order_index: i
      }));
    setDesigns(records);
    return records;
  }, []);

  const updateDesignImage = useCallback((designId, imageUrl) => {
    setDesigns(prev => prev.map(d => d.id === designId ? { ...d, image_url: imageUrl } : d));
  }, []);

  const swipeDesign = useCallback(async (designId, result, comment = '') => {
    setDesigns(prev => prev.map(d => d.id === designId
      ? { ...d, swipe_result: result, swipe_comment: comment.trim() }
      : d));
  }, []);

  const saveFinalLook = useCallback(async (data) => {
    if (session) setSession(prev => ({ ...prev, status: 'products' }));
    setFinalLook(data);
  }, [session]);

  const updateFinalLook = useCallback((data) => {
    setFinalLook(prev => ({ ...prev, ...data }));
  }, []);

  const addToCart = useCallback((product) => {
    setCart(prev => prev.find(p => p.id === product.id) ? prev : [...prev, product]);
  }, []);

  const removeFromCart = useCallback((productId) => {
    setCart(prev => prev.filter(p => p.id !== productId));
  }, []);

  const clearCart = useCallback(() => setCart([]), []);

  const reset = useCallback(() => {
    setQuestionnaire(null);
    setSession(null);
    setDesigns([]);
    setFinalLook(null);
    setMatchedProducts([]);
    setCart([]);
  }, []);

  const value = {
    questionnaire, setQuestionnaire,
    session, createSession,
    designs, saveDesigns, updateDesignImage, swipeDesign,
    finalLook, saveFinalLook, updateFinalLook,
    matchedProducts, setMatchedProducts,
    cart, addToCart, removeFromCart, clearCart,
    reset
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
