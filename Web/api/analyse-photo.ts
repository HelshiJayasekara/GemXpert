// POST /api/analyse-photo  {"prompt": str, "images": [{"mediaType": str, "data": base64}]}
//   -> {"ok": true, "value": {...}} or {"ok": false, "code": str, "message": str}
import { analysePhoto, clientIp } from "./_lib/photo.js";

export const config = { maxDuration: 120 };

export async function POST(request: Request): Promise<Response> {
  const origin = request.headers.get("origin");
  if (origin && new URL(origin).host !== new URL(request.url).host) {
    return Response.json({ ok: false, code: "forbidden", message: "Cross-site request refused." }, { status: 403 });
  }
  let body: unknown;
  try { body = await request.json(); }
  catch { return Response.json({ ok: false, code: "image_rejected", message: "Request wasn't JSON." }, { status: 400 }); }
  return Response.json(await analysePhoto(body, clientIp(request)), { headers: { "Cache-Control": "no-store" } });
}
