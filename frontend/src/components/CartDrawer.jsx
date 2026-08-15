import { motion, AnimatePresence } from 'framer-motion';
import { X, ShoppingBag, Check, ExternalLink } from 'lucide-react';
import { Image } from '@/components/ui/image';
import { Button } from '@/components/ui/button';

export default function CartDrawer({
  open,
  onClose,
  cart,
  onRemove,
  totalMinor,
  budgetMinor,
  onCreateCarts,
  creating,
  carts,
  failures,
  error
}) {
  const remainingMinor = budgetMinor - totalMinor;
  const money = value => (value / 100).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });

  return (
    <AnimatePresence>
      {open ? (
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

            <div className="flex-1 overflow-y-auto p-6 space-y-3 no-scrollbar">
              {cart.length === 0 ? (
                <p className="text-muted-foreground text-center py-16 text-sm">
                  Your cart is empty.<br />Add products to build your room.
                </p>
              ) : cart.map(item => (
                <div key={item.variantId} className="flex gap-3 items-start p-3 rounded border border-border bg-secondary/50">
                  <div className="w-14 h-14 rounded overflow-hidden flex-shrink-0 bg-background">
                    <Image src={item.imageUrl} fittingType="fill" className="w-full h-full" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-muted-foreground uppercase tracking-wider">{item.merchantName}</div>
                    <div className="font-display text-sm leading-snug">{item.title}</div>
                    <div className="text-sm font-display text-foreground mt-0.5">${money(item.priceMinor)}</div>
                  </div>
                  <button
                    onClick={() => onRemove(item.variantId)}
                    className="text-muted-foreground hover:text-destructive transition-colors p-1 rounded hover:bg-destructive/10"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}

              {carts.length > 0 ? (
                <div className="pt-4 space-y-3">
                  <h3 className="font-display text-lg flex items-center gap-2">
                    <Check className="w-4 h-4" /> Merchant carts ready
                  </h3>
                  {carts.map(cartResult => (
                    <a
                      key={cartResult.cartId}
                      href={cartResult.continueUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between rounded border border-border p-3 hover:border-foreground/40 transition-colors"
                    >
                      <span>
                        <span className="block text-sm font-medium">{cartResult.merchantName}</span>
                        <span className="block text-xs text-muted-foreground">${money(cartResult.subtotalMinor)}</span>
                      </span>
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  ))}
                </div>
              ) : null}

              {failures.length > 0 ? (
                <div className="rounded border border-destructive/30 bg-destructive/5 p-3 text-sm">
                  <p className="font-medium mb-1">Some merchant carts could not be created</p>
                  {failures.map(failure => (
                    <p key={`${failure.merchantDomain}-${failure.slotIds.join('-')}`} className="text-muted-foreground">
                      {failure.merchantDomain}: {failure.detail}
                    </p>
                  ))}
                </div>
              ) : null}

              {error ? <p className="text-sm text-destructive" role="alert">{error}</p> : null}
            </div>

            <div className="p-6 border-t border-border space-y-3">
              <div className="flex justify-between items-baseline">
                <span className="text-muted-foreground text-sm">Total</span>
                <span className="font-display text-2xl">${money(totalMinor)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground text-sm">Budget</span>
                <span className="text-sm text-foreground/80">${money(budgetMinor)}</span>
              </div>
              <div className={`text-sm ${remainingMinor >= 0 ? 'text-foreground/60' : 'text-destructive'}`}>
                {remainingMinor >= 0
                  ? `$${money(remainingMinor)} remaining`
                  : `$${money(Math.abs(remainingMinor))} over budget`}
              </div>
              <Button
                variant="outline"
                className="w-full rounded-full border-foreground text-foreground hover:bg-foreground hover:text-background tracking-wider uppercase text-sm font-normal h-12"
                size="lg"
                disabled={cart.length === 0 || creating}
                onClick={onCreateCarts}
              >
                {creating ? 'Creating merchant carts…' : 'Create Shopify Carts'}
              </Button>
            </div>
          </motion.div>
        </>
      ) : null}
    </AnimatePresence>
  );
}
