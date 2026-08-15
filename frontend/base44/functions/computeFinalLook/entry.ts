import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';

export default async function(req: Request): Promise<Response> {
  try {
    const base44 = createClientFromRequest(req);
    const body = await req.json();
    const { questionnaire, liked_designs, passed_designs } = body;

    const prefs = questionnaire.style_preferences && questionnaire.style_preferences.length > 0
      ? questionnaire.style_preferences.join(', ')
      : 'open to suggestions';

    const likedText = liked_designs && liked_designs.length > 0
      ? liked_designs.map(d =>
          `- ${d.style_name}: ${d.description} (warmth=${d.style_metadata.warmth}, minimalism=${d.style_metadata.minimalism}, natural_materials=${d.style_metadata.natural_materials}, colorfulness=${d.style_metadata.colorfulness}, modern=${d.style_metadata.modern}, vintage=${d.style_metadata.vintage})`
        ).join('\n')
      : 'No designs were liked. Use the questionnaire preferences.';

    const passedText = passed_designs && passed_designs.length > 0
      ? passed_designs.map(d => `- ${d.style_name}: ${d.description}`).join('\n')
      : 'No designs were passed on.';

    const prompt = `You are an expert interior designer AI. A user has swiped through 10 room design variations and liked some while passing on others. Based on their preferences, create a personalized final room design.

User context:
- Room type: ${questionnaire.room_type}
- Budget: ${questionnaire.budget}
- Age range: ${questionnaire.age}
- Main goal: ${questionnaire.goal}
- Style preference: ${prefs}

Designs the user LIKED:
${likedText}

Designs the user PASSED on:
${passedText}

Based on what the user liked (and avoided), create a personalized final room design that synthesizes their taste. The design should feel like a natural evolution of the styles they gravitated toward.

Provide:
1. style_profile: Numeric scores (0.0 to 1.0) reflecting the user's revealed preferences: warmth, minimalism, natural_materials, colorfulness, modern, vintage. Weight these toward what the user liked and away from what they passed on.
2. final_look_description: A 2-3 sentence vivid description of the personalized final room design
3. final_look_prompt: A detailed, vivid prompt for generating a photorealistic interior design photo of this final room. Describe the room type, specific furniture, colors, materials, lighting, and decor. Start with "Photorealistic interior design photograph of a ${questionnaire.room_type}, "
4. product_intents: An array of 5-7 product items needed to build this room. Each item should have:
   - item: The product category (e.g., "sofa", "coffee table", "floor lamp", "area rug", "wall art", "throw pillow", "bookshelf")
   - description: A specific description of the product (e.g., "beige boucle sofa with curved arms")
   - search_terms: Keywords for finding this product (e.g., "beige boucle sofa")
   - estimated_price: Estimated price in USD (keep total within budget)
   - color: Primary color
   - material: Primary material
   - style: Style descriptor

Keep the total estimated price of all product intents within the user's budget of ${questionnaire.budget}.`;

    const responseSchema = {
      type: "object",
      properties: {
        style_profile: {
          type: "object",
          properties: {
            warmth: { type: "number" },
            minimalism: { type: "number" },
            natural_materials: { type: "number" },
            colorfulness: { type: "number" },
            modern: { type: "number" },
            vintage: { type: "number" }
          },
          required: ["warmth", "minimalism", "natural_materials", "colorfulness", "modern", "vintage"]
        },
        final_look_description: { type: "string" },
        final_look_prompt: { type: "string" },
        product_intents: {
          type: "array",
          items: {
            type: "object",
            properties: {
              item: { type: "string" },
              description: { type: "string" },
              search_terms: { type: "string" },
              estimated_price: { type: "number" },
              color: { type: "string" },
              material: { type: "string" },
              style: { type: "string" }
            },
            required: ["item", "description", "search_terms", "estimated_price", "color", "material", "style"]
          }
        }
      },
      required: ["style_profile", "final_look_description", "final_look_prompt", "product_intents"]
    };

    const result = await base44.asServiceRole.integrations.Core.InvokeLLM({
      prompt,
      response_json_schema: responseSchema
    });

    return Response.json(result);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}