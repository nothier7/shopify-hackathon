import test from 'node:test';
import assert from 'node:assert/strict';

import {
  cartFailureNotice,
  groupProductOptions,
  mergeRankedProductOptions,
  productOfferPayload
} from './productOptions.js';

const lampOne = offer('lamp-one', 'lamp-slot', 'Bellaria Homestore');
const lampTwo = offer('lamp-two', 'lamp-slot', 'Lighting Loft');
const rug = offer('rug-one', 'rug-slot', 'Rug House');

test('keeps every candidate while marking the ML-selected best match', () => {
  const options = mergeRankedProductOptions(
    [lampOne, lampTwo, rug],
    [{ ...lampTwo, matchScore: 0.91 }, { ...rug, matchScore: 0.84 }]
  );

  assert.equal(options.length, 3);
  assert.equal(options[0].bestMatch, false);
  assert.equal(options[1].bestMatch, true);
  assert.equal(options[1].matchScore, 0.91);
});

test('groups alternatives in manifest item order', () => {
  const groups = groupProductOptions(
    { productSlots: [{ id: 'rug-slot' }, { id: 'lamp-slot' }] },
    [lampOne, rug, lampTwo]
  );

  assert.deepEqual(groups.map(group => group.slot.id), ['rug-slot', 'lamp-slot']);
  assert.deepEqual(groups[1].offers.map(item => item.variantId), ['lamp-one', 'lamp-two']);
});

test('turns unavailable variant details into an actionable customer message', () => {
  const notice = cartFailureNotice(
    {
      merchantDomain: 'bellaria-homestore.myshopify.com',
      slotIds: ['lamp-slot'],
      detail: 'selected variant is no longer available'
    },
    [lampOne],
    new Map([['lamp-slot', { category: 'Floor Lamp' }]])
  );

  assert.equal(notice.slotId, 'lamp-slot');
  assert.equal(
    notice.message,
    'The floor lamp from Bellaria Homestore is no longer available. Choose another match and try again.'
  );
  assert.equal(notice.message.includes('variant'), false);
  assert.equal(notice.message.includes('myshopify.com'), false);
});

test('removes UI-only metadata from cart API offers', () => {
  const payload = productOfferPayload({
    ...lampOne,
    bestMatch: true,
    temporaryCardState: 'selected'
  });

  assert.equal(payload.productId, lampOne.productId);
  assert.equal('bestMatch' in payload, false);
  assert.equal('temporaryCardState' in payload, false);
});

function offer(variantId, slotId, merchantName) {
  return {
    productId: `product-${variantId}`,
    variantId,
    slotId,
    merchantName,
    merchantDomain: `${merchantName.toLowerCase().replaceAll(' ', '-')}.myshopify.com`,
    priceMinor: 10_000
  };
}
