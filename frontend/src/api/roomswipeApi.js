const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const API_BASE_URL = (
  import.meta.env.VITE_ROOMSWIPE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '');

export class RoomSwipeApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = 'RoomSwipeApiError';
    this.status = status;
    this.details = details;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new RoomSwipeApiError(
      errorMessage(payload, response.status),
      response.status,
      payload
    );
  }
  return payload;
}

function jsonRequest(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}

function errorMessage(payload, status) {
  if (typeof payload === 'string' && payload.trim()) return payload;
  if (typeof payload?.detail === 'string') return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map(item => item.msg || 'Invalid request').join('. ');
  }
  return `RoomSwipe request failed (${status})`;
}

export function questionnaireToApi(questionnaire) {
  const style = questionnaire.style_preferences?.[0];
  return {
    roomType: questionnaire.room_type.toLowerCase(),
    budgetMinor: budgetToMinor(questionnaire.budget),
    currency: 'USD',
    effort: 'buy_only',
    designDensity: style === 'Maximalist' ? 'maximalist' : 'minimalist',
    userAge: ageToNumber(questionnaire.age),
    goals: [questionnaire.goal],
    optionalStyles: style && style !== 'No preference' ? [style] : []
  };
}

export function budgetToMinor(budget) {
  const dollars = Number.parseInt(String(budget || '').replace(/[^0-9]/g, ''), 10);
  return Number.isFinite(dollars) ? dollars * 100 : 0;
}

export function ageToNumber(age) {
  if (age === '65+') return 68;
  const [minimum, maximum] = String(age || '').split('-').map(Number);
  if (!Number.isFinite(minimum)) return 18;
  if (!Number.isFinite(maximum)) return minimum;
  return Math.round((minimum + maximum) / 2);
}

export async function generateDesigns(file, questionnaire, count = 10) {
  const form = new FormData();
  form.append('image', file);
  form.append('questionnaire', JSON.stringify(questionnaireToApi(questionnaire)));
  form.append('count', String(count));
  return request('/images/generate-designs', { method: 'POST', body: form });
}

export function learnPreferences(candidates, swipes, prior = null) {
  return jsonRequest('/recommendations/preferences', {
    candidates: candidates.map(candidateToApi),
    swipes,
    ...(prior ? { prior } : {})
  });
}

export function finalizeRecommendation(candidates, swipes) {
  return jsonRequest('/recommendations/finalize', {
    candidates: candidates.map(candidateToApi),
    swipes
  });
}

function candidateToApi(candidate) {
  const apiCandidate = { ...candidate };
  delete apiCandidate.swipe_result;
  return apiCandidate;
}

export async function generateFinalDesign(file, recommendedDesign) {
  const form = new FormData();
  form.append('image', file);
  form.append('recommended_design', JSON.stringify(recommendedDesign));
  return request('/images/generate-final', { method: 'POST', body: form });
}

export function searchProducts(manifest, budgetMinor, candidatesPerSlot = 3) {
  return jsonRequest('/commerce/search', {
    manifest,
    budgetMinor,
    currency: 'USD',
    country: 'US',
    candidatesPerSlot
  });
}

export function selectProducts(profile, offers, budgetMinor) {
  return jsonRequest('/recommendations/select-products', {
    profile,
    offers,
    budgetMinor
  });
}

export function createCarts(offers) {
  return jsonRequest('/commerce/carts', { offers, country: 'US' });
}
