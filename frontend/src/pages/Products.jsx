import { useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShoppingBag, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Image } from '@/components/ui/image';
import ProductCard from '@/components/ProductCard';
import CartDrawer from '@/components/CartDrawer';
import { useSession } from '@/lib/SessionContext';
import {
  groupProductOptions,
  mergeRankedProductOptions
} from '@/lib/productOptions';
import {
  budgetToMinor,
  createCarts,
  searchProducts,
  selectProducts
} from '@/api/roomswipeApi';

export default function Products() {
  const {
    questionnaire,
    recommendedDesign,
    manifest,
    preferenceProfile,
    offers,
    setOffers,
    selectedOffers,
    selectOffer,
    removeOffer,
    merchantCarts,
    cartFailures,
    saveCartResult
  } = useSession();
  const [loading, setLoading] = useState(offers.length === 0);
  const [searchError, setSearchError] = useState('');
  const [cartError, setCartError] = useState('');
  const [cartOpen, setCartOpen] = useState(false);
  const [creatingCarts, setCreatingCarts] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const budgetMinor = budgetToMinor(questionnaire?.budget);

  useEffect(() => {
    if (!manifest || !preferenceProfile || !budgetMinor || offers.length > 0) return undefined;
    let cancelled = false;

    const findProducts = async () => {
      setLoading(true);
      setSearchError('');
      try {
        const candidates = await searchProducts(manifest, budgetMinor);
        const ranked = await selectProducts(preferenceProfile, candidates, budgetMinor);
        if (cancelled) return;
        setOffers(mergeRankedProductOptions(candidates, ranked));
        setLoading(false);
      } catch (requestError) {
        if (cancelled) return;
        console.error(requestError);
        setSearchError(requestError.message || 'Shopify product search failed.');
        setLoading(false);
      }
    };

    findProducts();
    return () => {
      cancelled = true;
    };
  }, [attempt, budgetMinor, manifest, offers.length, preferenceProfile, setOffers]);

  const offerGroups = useMemo(
    () => groupProductOptions(manifest, offers),
    [manifest, offers]
  );
  const selectedBySlot = useMemo(
    () => new Map(selectedOffers.map(offer => [offer.slotId, offer])),
    [selectedOffers]
  );
  const slotLookup = useMemo(
    () => new Map(offerGroups.map(group => [group.slot.id, group.slot])),
    [offerGroups]
  );

  if (!manifest || !preferenceProfile || !questionnaire) {
    return <Navigate to="/final" replace />;
  }

  const totalMinor = selectedOffers.reduce((sum, item) => sum + item.priceMinor, 0);
  const merchants = new Set(offers.map(product => product.merchantDomain));

  const handleCreateCarts = async () => {
    if (creatingCarts || selectedOffers.length === 0) return;
    setCreatingCarts(true);
    setCartError('');
    try {
      const result = await createCarts(selectedOffers);
      saveCartResult(result);
    } catch (requestError) {
      console.error(requestError);
      setCartError(requestError.message || 'Merchant cart creation failed.');
    } finally {
      setCreatingCarts(false);
    }
  };

  const handleChooseAlternative = (slotId) => {
    setCartOpen(false);
    window.setTimeout(() => {
      document.getElementById(`product-options-${slotId}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }, 220);
  };

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center px-6">
        <div className="w-10 h-10 rounded-full border border-foreground/20 border-t-foreground animate-spin mb-8" />
        <p className="font-display text-2xl mb-2">Searching live Shopify products</p>
        <p className="text-muted-foreground font-light">Ranking real products against your learned style…</p>
      </div>
    );
  }

  if (searchError) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center px-6 text-center">
        <p className="font-display text-2xl mb-3">Product search needs another try</p>
        <p className="text-muted-foreground max-w-lg mb-6" role="alert">{searchError}</p>
        <Button variant="outline" onClick={() => setAttempt(value => value + 1)} className="rounded-full">
          <RotateCw className="w-4 h-4 mr-2" /> Retry Shopify search
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-12 pb-32">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="flex flex-col sm:flex-row gap-6 mb-10">
          <div className="w-full sm:w-48 h-36 rounded overflow-hidden border border-border flex-shrink-0 bg-secondary">
            <Image src={manifest.finalImageUrl} fittingType="fill" className="w-full h-full" />
          </div>
          <div className="flex-1 flex flex-col justify-center">
            <div className="text-xs uppercase tracking-widest text-muted-foreground mb-3">Live Shopify matches</div>
            <h1 className="font-display text-2xl sm:text-3xl mb-2">
              {recommendedDesign?.name || 'Your room'}, <span className="italic">shoppable</span>
            </h1>
            <p className="text-muted-foreground text-sm font-light">
              {offerGroups.length} room items · {offers.length} choices from {merchants.size} {merchants.size === 1 ? 'merchant' : 'merchants'} · Budget {questionnaire.budget}
            </p>
          </div>
        </div>

        {offers.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-muted-foreground font-light">No US-shippable Shopify products matched this room.</p>
          </div>
        ) : (
          <div className="space-y-14">
            {offerGroups.map((group, groupIndex) => {
              const selected = selectedBySlot.get(group.slot.id);
              return (
                <section
                  id={`product-options-${group.slot.id}`}
                  key={group.slot.id}
                  className="scroll-mt-24 border-t border-border pt-7"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between mb-5">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground mb-2">
                        Item {String(groupIndex + 1).padStart(2, '0')}
                      </div>
                      <h2 className="font-display text-2xl capitalize">{group.slot.category}</h2>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {group.offers.length} {group.offers.length === 1 ? 'match' : 'matches'}
                      {selected ? ` · ${selected.merchantName} selected` : ' · Choose one'}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {group.offers.map((product, optionIndex) => (
                      <motion.div
                        key={`${product.productId}:${product.variantId}`}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: optionIndex * 0.05 }}
                      >
                        <ProductCard
                          product={product}
                          onChoose={selectOffer}
                          selected={selected?.variantId === product.variantId}
                          hasSelection={Boolean(selected)}
                        />
                      </motion.div>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </motion.div>

      {selectedOffers.length > 0 ? (
        <motion.div initial={{ y: 100 }} animate={{ y: 0 }} className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30">
          <Button onClick={() => setCartOpen(true)} size="lg" className="rounded-full shadow-2xl px-6 gap-2 h-14">
            <ShoppingBag className="w-4 h-4" strokeWidth={1.5} />
            {selectedOffers.length} {selectedOffers.length === 1 ? 'item' : 'items'} · ${(totalMinor / 100).toLocaleString()}
            <span className="ml-1 text-xs tracking-wider uppercase opacity-80">View Cart</span>
          </Button>
        </motion.div>
      ) : null}

      <CartDrawer
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        cart={selectedOffers}
        onRemove={removeOffer}
        totalMinor={totalMinor}
        budgetMinor={budgetMinor}
        onCreateCarts={handleCreateCarts}
        creating={creatingCarts}
        carts={merchantCarts}
        failures={cartFailures}
        error={cartError}
        slotLookup={slotLookup}
        onChooseAlternative={handleChooseAlternative}
      />
    </div>
  );
}
