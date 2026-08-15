import { Image } from '@/components/ui/image';
import { Button } from '@/components/ui/button';
import { Check, Plus } from 'lucide-react';

export default function ProductCard({ product, onAddToCart, inCart }) {
  const price = (product.priceMinor / 100).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
  const match = product.matchScore == null ? null : Math.round(product.matchScore * 100);

  return (
    <div className="group rounded-lg border border-border bg-card overflow-hidden transition-all duration-300 hover:border-foreground/30">
      <div className="aspect-square overflow-hidden bg-secondary">
        <Image
          src={product.imageUrl}
          fittingType="fill"
          className="w-full h-full transition-transform duration-700 group-hover:scale-105"
        />
      </div>
      <div className="p-4">
        <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
          {product.merchantName}
        </div>
        <h3 className="font-display text-base mb-1 leading-snug">{product.title}</h3>
        <p className="text-xs text-muted-foreground mb-4 line-clamp-2 italic leading-relaxed">
          {match == null ? 'Live Shopify catalog match' : `${match}% preference match`}
          {product.relaxedPreferences?.length
            ? ` · Similar match with ${product.relaxedPreferences.join(', ')} relaxed`
            : ''}
        </p>
        <div className="flex items-center justify-between">
          <span className="font-display text-lg">${price}</span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onAddToCart(product)}
            disabled={inCart}
            className="rounded-full border-foreground/30 text-foreground hover:bg-foreground hover:text-background hover:border-foreground px-4 font-normal"
          >
            {inCart ? (
              <><Check className="w-3.5 h-3.5 mr-1" strokeWidth={2} /> Added</>
            ) : (
              <><Plus className="w-3.5 h-3.5 mr-1" /> Add</>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
