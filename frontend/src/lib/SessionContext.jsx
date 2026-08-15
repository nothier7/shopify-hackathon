import React, { createContext, useCallback, useContext, useRef, useState } from 'react';

const SessionContext = createContext(null);

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error('useSession must be used within SessionProvider');
  return context;
}

export function SessionProvider({ children }) {
  const [questionnaire, setQuestionnaire] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState(null);
  const [designs, setDesigns] = useState([]);
  const [swipes, setSwipes] = useState([]);
  const [preferenceProfile, setPreferenceProfile] = useState(null);
  const [recommendedDesign, setRecommendedDesign] = useState(null);
  const [manifest, setManifest] = useState(null);
  const [offers, setOffers] = useState([]);
  const [selectedOffers, setSelectedOffers] = useState([]);
  const [merchantCarts, setMerchantCarts] = useState([]);
  const [cartFailures, setCartFailures] = useState([]);
  const previewUrlRef = useRef(null);

  const savePhoto = useCallback((file, previewUrl) => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = previewUrl;
    setPhotoFile(file);
    setPhotoPreviewUrl(previewUrl);
  }, []);

  const saveDesigns = useCallback((candidates) => {
    setDesigns(candidates.map(candidate => ({ ...candidate, swipe_result: 'pending' })));
    setSwipes([]);
  }, []);

  const swipeDesign = useCallback((designId, result) => {
    const liked = result === 'like';
    setDesigns(current => current.map(design => (
      design.id === designId ? { ...design, swipe_result: result } : design
    )));
    setSwipes(current => [
      ...current.filter(swipe => swipe.candidateId !== designId),
      { candidateId: designId, liked }
    ]);
  }, []);

  const saveRecommendation = useCallback((profile, design) => {
    setPreferenceProfile(profile);
    setRecommendedDesign(design);
  }, []);

  const selectOffer = useCallback((offer) => {
    setSelectedOffers(current => [
      ...current.filter(selected => selected.slotId !== offer.slotId),
      offer
    ]);
  }, []);

  const removeOffer = useCallback((variantId) => {
    setSelectedOffers(current => current.filter(offer => offer.variantId !== variantId));
  }, []);

  const saveCartResult = useCallback((result) => {
    setMerchantCarts(result.carts || []);
    setCartFailures(result.failures || []);
  }, []);

  const reset = useCallback(() => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = null;
    setQuestionnaire(null);
    setPhotoFile(null);
    setPhotoPreviewUrl(null);
    setDesigns([]);
    setSwipes([]);
    setPreferenceProfile(null);
    setRecommendedDesign(null);
    setManifest(null);
    setOffers([]);
    setSelectedOffers([]);
    setMerchantCarts([]);
    setCartFailures([]);
  }, []);

  const value = {
    questionnaire,
    setQuestionnaire,
    photoFile,
    photoPreviewUrl,
    savePhoto,
    designs,
    saveDesigns,
    swipes,
    swipeDesign,
    preferenceProfile,
    recommendedDesign,
    saveRecommendation,
    manifest,
    setManifest,
    offers,
    setOffers,
    selectedOffers,
    setSelectedOffers,
    selectOffer,
    removeOffer,
    merchantCarts,
    cartFailures,
    saveCartResult,
    reset
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
