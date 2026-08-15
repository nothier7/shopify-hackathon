import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShoppingBag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Image } from '@/components/ui/image';
import ProductCard from '@/components/ProductCard';
import CartDrawer from '@/components/CartDrawer';
import { useSession } from '@/lib/SessionContext';
import { createCarts, searchProducts } from '@/api/roomswipeClient';

export default function Products() {
  const navigate = useNavigate();
  const { session, finalLook, matchedProducts, setMatchedProducts, cart, addToCart, removeFromCart } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cartOpen, setCartOpen] = useState(false);
  const matchedRef = useRef(false);

  useEffect(() => {
    if (!finalLook) {
      navigate('/');
      return;
    }
    if (matchedRef.current) return;
    matchedRef.current = true;
    if (matchedProducts.length > 0) {
      setLoading(false);
      return;
    }

    const match = async () => {
      try {
        const offers = await searchProducts(finalLook.manifest, session.budget_value * 100);
        setMatchedProducts(offers.map(offer => ({
          id: `${offer.productId}:${offer.variantId}`,
          name: offer.title,
          merchant: offer.merchantName,
          price: offer.priceMinor / 100,
          image_url: offer.imageUrl,
          match_reason: offer.relaxedPreferences?.length
            ? `Matched with relaxed ${offer.relaxedPreferences.join(', ')} preferences.`
            : 'Matched to the recommended room item and budget.',
          raw_offer: offer,
        })));
      } catch (err) {
        console.error(err);
        setError(err.message || 'Could not find Shopify products.');
      }
      setLoading(false);
    };
    match();
  }, []);

  if (!finalLook) return null;

  const createShopifyCarts = async (selectedProducts) => {
    return createCarts(selectedProducts.map(product => product.raw_offer));
  };

  const cartTotal = cart.reduce((sum, item) => sum + item.price, 0);
  const merchants = new Set(matchedProducts.map(p => p.merchant));

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center px-6">
        <div className="w-10 h-10 rounded-full border border-foreground/20 border-t-foreground animate-spin mb-8" />
        <p className="font-display text-2xl mb-2">Finding real products</p>
        <p className="text-muted-foreground font-light">Matching your room design to shoppable furniture…</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-12 pb-32">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="flex flex-col sm:flex-row gap-6 mb-10">
          <div className="w-full sm:w-48 h-36 rounded overflow-hidden border border-border flex-shrink-0 bg-secondary">
            <Image src={finalLook.final_look_url} fittingType="fill" className="w-full h-full" />
          </div>
          <div className="flex-1 flex flex-col justify-center">
            <div className="text-xs uppercase tracking-widest text-muted-foreground mb-3">Your Room</div>
            <h1 className="font-display text-2xl sm:text-3xl mb-2">Your room, <span className="italic">shoppable</span></h1>
            <p className="text-muted-foreground text-sm font-light">
              {matchedProducts.length} products from {merchants.size} {merchants.size === 1 ? 'merchant' : 'merchants'} · Budget {session.budget}
            </p>
          </div>
        </div>

        {matchedProducts.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-muted-foreground font-light">{error || 'No products matched your room. Try regenerating your final look.'}</p>
            <Button variant="outline" onClick={() => navigate('/final')} className="mt-4 rounded-full">Back to Final Look</Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {matchedProducts.map((product, i) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
              >
                <ProductCard
                  product={product}
                  onAddToCart={addToCart}
                  inCart={cart.some(c => c.id === product.id)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {cart.length > 0 && (
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30"
        >
          <Button
            onClick={() => setCartOpen(true)}
            size="lg"
            className="rounded-full shadow-2xl px-6 gap-2 h-14"
          >
            <ShoppingBag className="w-4 h-4" strokeWidth={1.5} />
            {cart.length} {cart.length === 1 ? 'item' : 'items'} · ${cartTotal}
            <span className="ml-1 text-xs tracking-wider uppercase opacity-80">View Cart</span>
          </Button>
        </motion.div>
      )}

      <CartDrawer
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        cart={cart}
        onRemove={removeFromCart}
        total={cartTotal}
        budgetValue={session.budget_value}
        budgetLabel={session.budget}
        onCreateCarts={createShopifyCarts}
      />
    </div>
  );
}
