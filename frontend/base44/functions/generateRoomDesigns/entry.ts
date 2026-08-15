import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';

export default async function(req: Request): Promise<Response> {
  try {
    const base44 = createClientFromRequest(req);
    const body = await req.json();
    const { room_type, budget, age, goal, style_preferences, photo_url } = body;

    const prefs = style_preferences && style_preferences.length > 0
      ? style_preferences.join(', ')
      : 'open to suggestions';

    const prompt = `You are an expert interior designer AI. A user wants to redesign their ${room_type}.

User context:
- Budget: ${budget}
- Age range: ${age}
- Main goal: ${goal}
- Style preference: ${prefs}

${photo_url ? 'I have attached a photo of their current room. Analyze the room architecture, layout, and major furniture, and design variations that work with this specific space.' : ''}

Generate exactly 10 distinct interior design variations for this ${room_type}. Each variation should explore a different aesthetic direction. Some should align with the user's stated preferences, while others should explore different styles to help the user discover what they like.

For each variation, provide:
1. style_name: A short, evocative name (e.g., "Warm Minimalist", "Japandi Serenity", "Industrial Loft")
2. description: A 1-2 sentence description of the design aesthetic and key elements
3. image_prompt: A detailed, vivid prompt for generating a photorealistic interior design photo of this room. Describe the room type, furniture pieces, color palette, materials, lighting, textures, and decor accessories. Make it specific and visual. Start with "Photorealistic interior design photograph of a ${room_type}, "
4. style_metadata: Numeric scores (0.0 to 1.0) for: warmth, minimalism, natural_materials, colorfulness, modern, vintage

Make all 10 variations visually and aesthetically distinct from each other. Include a mix of styles: some warm and cozy, some minimal and clean, some colorful, some industrial, some natural/organic, some vintage, some modern.`;

    const responseSchema = {
      type: "object",
      properties: {
        designs: {
          type: "array",
          items: {
            type: "object",
            properties: {
              style_name: { type: "string" },
              description: { type: "string" },
              image_prompt: { type: "string" },
              style_metadata: {
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
              }
            },
            required: ["style_name", "description", "image_prompt", "style_metadata"]
          }
        }
      },
      required: ["designs"]
    };

    const result = await base44.asServiceRole.integrations.Core.InvokeLLM({
      prompt,
      response_json_schema: responseSchema,
      file_urls: photo_url ? [photo_url] : undefined
    });

    return Response.json(result);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}