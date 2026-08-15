import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';

export default async function(req: Request): Promise<Response> {
  try {
    const base44 = createClientFromRequest(req);
    const body = await req.json();
    const { current_prompt, current_description, direction, questionnaire } = body;

    const prompt = `You are an expert interior designer AI. A user has a personalized room design and wants to iterate on it.

Current room design description: ${current_description}
Current image prompt: ${current_prompt}

The user wants it to be: ${direction}

Room type: ${questionnaire.room_type}
Budget: ${questionnaire.budget}

Adjust the room design to be more ${direction} while keeping it cohesive and within budget. Provide:
1. final_look_description: A 2-3 sentence vivid description of the updated room design
2. final_look_prompt: A detailed, vivid prompt for generating a photorealistic interior design photo of this updated room. Start with "Photorealistic interior design photograph of a ${questionnaire.room_type}, "`;

    const responseSchema = {
      type: "object",
      properties: {
        final_look_description: { type: "string" },
        final_look_prompt: { type: "string" }
      },
      required: ["final_look_description", "final_look_prompt"]
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