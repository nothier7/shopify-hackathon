const API_ROOT = (import.meta.env.VITE_ROOMSWIPE_API_URL || '/api/v1').replace(/\/$/, '');

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, options);
  if (response.ok) return response.json();

  let detail = `RoomSwipe API request failed (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body.detail === 'string') detail = body.detail;
    else if (body.detail) detail = JSON.stringify(body.detail);
  } catch {
    // Keep the status-based fallback for non-JSON upstream failures.
  }
  throw new Error(detail);
}

function jsonOptions(body) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export function toApiQuestionnaire(questionnaire) {
  const ageStart = Number.parseInt(questionnaire.age, 10);
  const budgetDollars = Number(questionnaire.budget_value)
    || Number.parseInt(String(questionnaire.budget).replace(/[^0-9]/g, ''), 10)
    || 0;
  const density = questionnaire.style_preferences?.[0] === 'Maximalist'
    ? 'maximalist'
    : 'minimalist';

  return {
    roomType: questionnaire.room_type,
    budgetMinor: budgetDollars * 100,
    currency: 'USD',
    effort: questionnaire.effort,
    designDensity: density,
    userAge: Number.isFinite(ageStart) ? ageStart : 18,
    goals: [questionnaire.goal],
    optionalStyles: questionnaire.style_preferences || [],
  };
}

export function generateDesigns(file, questionnaire) {
  const form = new FormData();
  form.append('image', file);
  form.append('questionnaire', JSON.stringify(toApiQuestionnaire(questionnaire)));
  form.append('count', '10');
  return apiRequest('/images/generate-designs', { method: 'POST', body: form });
}

export function finalizeRecommendation(candidates, swipes) {
  return apiRequest('/recommendations/finalize', jsonOptions({ candidates, swipes }));
}

export function generateFinalDesign(file, recommendation, refinement = null) {
  const form = new FormData();
  form.append('image', file);
  form.append('recommendation', JSON.stringify(recommendation));
  if (refinement) form.append('refinement', refinement);
  return apiRequest('/images/generate-final-design', { method: 'POST', body: form });
}

export function searchProducts(manifest, budgetMinor) {
  return apiRequest('/commerce/search', jsonOptions({
    manifest,
    budgetMinor,
    currency: 'USD',
    country: 'US',
    candidatesPerSlot: 3,
  }));
}

export function createCarts(offers) {
  return apiRequest('/commerce/carts', jsonOptions({ offers, country: 'US' }));
}
