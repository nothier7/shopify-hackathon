import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';

export default async function(req: Request): Promise<Response> {
  try {
    const base44 = createClientFromRequest(req);
    const body = await req.json();
    const { product_intents, budget } = body;

    const products = await base44.asServiceRole.entities.Product.list();

    const intentsText = product_intents.map((intent, idx) =>
      `${idx + 1}. ${intent.item}: ${intent.description} (search: "${intent.search_terms}", color: ${intent.color}, material: ${intent.material}, style: ${intent.style}, estimated price: $${intent.estimated_price})`
    ).join('\n');

    const catalogText = products.map(p =>
      `- ID: ${p.id} | ${p.name} | category: ${p.category} | $${p.price} | style: ${p.style} | color: ${p.color} | material: ${p.material} | ${p.description}`
    ).join('\n');

    const prompt = `You are a product matching AI for an interior design shopping app. Match each product intent from a room design to the best available product in the catalog.

Product intents (what the room design needs):
${intentsText}

Available product catalog:
${catalogText}

For each product intent, find the best matching product from the catalog. Consider category, style, color, material, and price. If no good match exists for an intent, skip it. Try to keep the total price of all matched products within $${budget}.

Return an array of matches, each with:
- intent_name: The item name from the product intent
- product_id: The ID of the matched product from the catalog
- match_reason: A brief explanation of why this product matches the intent
- match_score: A score from 0.0 to 1.0 indicating match quality`;

    const responseSchema = {
      type: "object",
      properties: {
        matches: {
          type: "array",
          items: {
            type: "object",
            properties: {
              intent_name: { type: "string" },
              product_id: { type: "string" },
              match_reason: { type: "string" },
              match_score: { type: "number" }
            },
            required: ["intent_name", "product_id", "match_reason", "match_score"]
          }
        }
      },
      required: ["matches"]
    };

    const result = await base44.asServiceRole.integrations.Core.InvokeLLM({
      prompt,
      response_json_schema: responseSchema
    });

    const productMap = {};
    for (const p of products) {
      productMap[p.id] = p;
    }

    const enrichedMatches = (result.matches || []).map(m => {
      const product = productMap[m.product_id];
      if (!product) return null;
      return {
        ...product,
        intent_name: m.intent_name,
        match_reason: m.match_reason,
        match_score: m.match_score
      };
    }).filter(Boolean);

    return Response.json({ matches: enrichedMatches });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}