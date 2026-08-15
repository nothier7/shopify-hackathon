const offerKey = offer => `${offer.productId}:${offer.variantId}`;
const PRODUCT_OFFER_FIELDS = [
  'productId',
  'variantId',
  'slotId',
  'title',
  'description',
  'merchantName',
  'merchantDomain',
  'priceMinor',
  'currency',
  'imageUrl',
  'checkoutUrl',
  'available',
  'matchScore',
  'relaxedPreferences'
];

export function mergeRankedProductOptions(candidates, rankedOffers) {
  const rankedByOffer = new Map(
    rankedOffers.map(offer => [offerKey(offer), offer])
  );

  return candidates.map(candidate => {
    const ranked = rankedByOffer.get(offerKey(candidate));
    return {
      ...candidate,
      ...(ranked?.matchScore == null ? {} : { matchScore: ranked.matchScore }),
      bestMatch: Boolean(ranked)
    };
  });
}

export function groupProductOptions(manifest, offers) {
  const offersBySlot = new Map();
  for (const offer of offers) {
    const slotOffers = offersBySlot.get(offer.slotId) || [];
    slotOffers.push(offer);
    offersBySlot.set(offer.slotId, slotOffers);
  }

  return (manifest?.productSlots || [])
    .map(slot => ({ slot, offers: offersBySlot.get(slot.id) || [] }))
    .filter(group => group.offers.length > 0);
}

export function productOfferPayload(offer) {
  return Object.fromEntries(
    PRODUCT_OFFER_FIELDS
      .filter(field => offer[field] !== undefined)
      .map(field => [field, offer[field]])
  );
}

export function cartFailureNotice(failure, cart, slotLookup) {
  const slotId = failure.slotIds?.[0] || null;
  const selectedOffer = cart.find(offer => failure.slotIds?.includes(offer.slotId));
  const slot = slotId ? slotLookup.get(slotId) : null;
  const itemName = sentenceCase(slot?.category || 'selected item');
  const merchantName = selectedOffer?.merchantName || merchantFromDomain(failure.merchantDomain);
  const unavailable = /no longer available|no purchasable variants/i.test(failure.detail || '');

  return {
    slotId,
    message: unavailable
      ? `The ${itemName} from ${merchantName} is no longer available. Choose another match and try again.`
      : `${merchantName} couldn't prepare the ${itemName} right now. Choose another match or try again in a moment.`
  };
}

function sentenceCase(value) {
  return String(value)
    .replace(/[-_]+/g, ' ')
    .trim()
    .toLowerCase();
}

function merchantFromDomain(domain) {
  const name = String(domain || 'This merchant').split('.')[0].replace(/[-_]+/g, ' ');
  return name.replace(/\b\w/g, letter => letter.toUpperCase());
}
