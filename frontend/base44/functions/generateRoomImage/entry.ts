import { createClientFromRequest } from 'npm:@base44/sdk@0.8.40';

export default async function(req: Request): Promise<Response> {
  try {
    const base44 = createClientFromRequest(req);
    const body = await req.json();
    const { prompt, reference_image_url } = body;

    const result = await base44.asServiceRole.integrations.Core.GenerateImage({
      prompt,
      existing_image_urls: reference_image_url ? [reference_image_url] : null
    });

    return Response.json({ url: result.url });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}