import { motion, AnimatePresence } from 'framer-motion';
import { X, ShoppingBag, Check } from 'lucide-react';
import { Image } from '@/components/ui/image';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

export default function CartDrawer({ open, onClose, cart, onRemove, total, budgetValue, budgetLabel, onCreateCarts }) {
  const [cartResult, setCartResult] = useState(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const handleCreateCart = async () => {
    setCreating(true);
    setError('');
    try {
      setCartResult(await onCreateCarts(cart));
    } catch (err) {
      setError(err.message || 'Could not create Shopify carts.');
    } finally {
      setCreating(false);
    }
  };

  const remaining = budgetValue - total;

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-card z-50 shadow-2xl flex flex-col border-l border-border"
          >
            <div className="flex items-center justify-between p-6 border-b border-border">
              <h2 className="font-display text-xl flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} /> Your Cart
              </h2>
              <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-full hover:bg-secondary">
                <X className="w-4 h-4" />
              </button>
            </div>

            {cartResult ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                  className="w-16 h-16 rounded-full border border-foreground flex items-center justify-center mb-6"
                >
                  <Check className="w-8 h-8 text-foreground" strokeWidth={1.5} />
                </motion.div>
                <h3 className="font-display text-2xl mb-2">Cart Created</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {cartResult.carts.length} merchant {cartResult.carts.length === 1 ? 'cart is' : 'carts are'} ready for checkout.
                </p>
                <div className="w-full mt-6 space-y-3">
                  {cartResult.carts.map(merchantCart => (
                    <a
                      key={merchantCart.cartId}
                      href={merchantCart.continueUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="block rounded-full border border-foreground px-5 py-3 text-sm hover:bg-foreground hover:text-background transition-colors"
                    >
                      Continue to {merchantCart.merchantName}
                    </a>
                  ))}
                  {cartResult.failures.map(failure => (
                    <p key={`${failure.merchantDomain}:${failure.slotIds.join(',')}`} className="text-sm text-destructive">
                      {failure.merchantDomain}: {failure.detail}
                    </p>
                  ))}
                </div>
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto p-6 space-y-3 no-scrollbar">
                  {cart.length === 0 ? (
                    <p className="text-muted-foreground text-center py-16 text-sm">
                      Your cart is empty.<br />Add products to build your room.
                    </p>
                  ) : (
                    cart.map(item => (
                      <div key={item.id} className="flex gap-3 items-start p-3 rounded border border-border bg-secondary/50">
                        <div className="w-14 h-14 rounded overflow-hidden flex-shrink-0 bg-background">
                          <Image src={item.image_url} fittingType="fill" className="w-full h-full" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-muted-foreground uppercase tracking-wider">{item.merchant}</div>
                          <div className="font-display text-sm leading-snug">{item.name}</div>
                          <div className="text-sm font-display text-foreground mt-0.5">${item.price}</div>
                        </div>
                        <button
                          onClick={() => onRemove(item.id)}
                          className="text-muted-foreground hover:text-destructive transition-colors p-1 rounded hover:bg-destructive/10"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                <div className="p-6 border-t border-border space-y-3">
                  <div className="flex justify-between items-baseline">
                    <span className="text-muted-foreground text-sm">Total</span>
                    <span className="font-display text-2xl">${total}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground text-sm">Budget</span>
                    <span className="text-sm text-foreground/80">{budgetLabel}</span>
                  </div>
                  <div className={`text-sm ${remaining >= 0 ? 'text-foreground/60' : 'text-destructive'}`}>
                    {remaining >= 0 ? `$${remaining} remaining` : `$${Math.abs(remaining)} over budget`}
                  </div>
                  <Button
                    variant="outline"
                    className="w-full rounded-full border-foreground text-foreground hover:bg-foreground hover:text-background tracking-wider uppercase text-sm font-normal h-12"
                    size="lg"
                    disabled={cart.length === 0 || creating}
                    onClick={handleCreateCart}
                  >
                    {creating ? 'Creating Carts…' : 'Create Cart'}
                  </Button>
                  {error && <p className="text-sm text-destructive text-center">{error}</p>}
                </div>
              </>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
