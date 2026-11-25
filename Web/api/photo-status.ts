// GET /api/photo-status -> {"available": bool, "reason": str}
import { photoStatus } from "./_lib/photo.js";

export function GET(): Response {
  return Response.json(photoStatus(), { headers: { "Cache-Control": "no-store" } });
}
