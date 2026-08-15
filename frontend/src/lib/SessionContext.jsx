import React, { createContext, useContext, useState, useCallback } from 'react';
import { base44 } from '@/api/base44Client';

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

  const createSession = useCallback(async (photoUrl) => {
    const s = await base44.entities.RoomSession.create({
      ...questionnaire,
      photo_url: photoUrl,
      budget_value: parseBudgetValue(questionnaire.budget),
      status: 'swiping'
    });
    setSession(s);
    return s;
  }, [questionnaire]);

  const saveDesigns = useCallback(async (designConcepts, sessionId) => {
    const records = await base44.entities.RoomDesign.bulkCreate(
      designConcepts.map((d, i) => ({
        session_id: sessionId,
        style_name: d.style_name,
        description: d.description,
        image_prompt: d.image_prompt,
        style_metadata: d.style_metadata,
        swipe_result: 'pending',
        order_index: i
      }))
    );
    setDesigns(records);
    return records;
  }, []);

  const updateDesignImage = useCallback((designId, imageUrl) => {
    setDesigns(prev => prev.map(d => d.id === designId ? { ...d, image_url: imageUrl } : d));
  }, []);

  const swipeDesign = useCallback(async (designId, result) => {
    setDesigns(prev => prev.map(d => d.id === designId ? { ...d, swipe_result: result } : d));
    await base44.entities.RoomDesign.update(designId, { swipe_result: result });
  }, []);

  const saveFinalLook = useCallback(async (data) => {
    if (session) {
      const updated = await base44.entities.RoomSession.update(session.id, {
        status: 'products',
        style_profile: data.style_profile,
        final_look_description: data.final_look_description,
        final_look_prompt: data.final_look_prompt,
        product_intents: data.product_intents,
        final_look_url: data.final_look_url
      });
      setSession(updated);
    }
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