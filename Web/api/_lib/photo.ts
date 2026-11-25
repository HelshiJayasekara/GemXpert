// Shared logic for the photo-analysis endpoints. Runs on the server only (Vercel function, or the Vite dev server):
// the Anthropic API key stays here and never reaches the browser.
import Anthropic from "@anthropic-ai/sdk";

const MODEL = "claude-opus-5-5";
const MEDIA_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const MAX_IMAGE_B64 = 7_000_000;            // ~5 MB of image; the page shrinks photos to 1568 px JPEG first
const RATE = { windowMs: 60 * 60 * 1000, max: 20 };   // per IP per hour, per server instance (best effort)
const hits = new Map<string, number[]>();

export type PhotoAnswer = { ok: true; value: Record<string, unknown> } | { ok: false; code: string; message: string };

export function photoStatus() {
  if (!process.env.ANTHROPIC_API_KEY) {
    return { available: false, reason: "Photo analysis isn't set up on this server yet (no ANTHROPIC_API_KEY)." };
  }
  return { available: true, reason: "" };
}

function rateLimited(ip: string) {
  const now = Date.now();
  const list = (hits.get(ip) || []).filter((t) => now - t < RATE.windowMs);
  list.push(now);
  hits.set(ip, list);
  return list.length > RATE.max;
}

function parseJsonAnswer(text: string): Record<string, unknown> {
  const fenced = /```(?:json)?\s*(\{[\s\S]*?\})\s*```/.exec(text);
  const candidate = fenced ? fenced[1] : text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1);
  const value = JSON.parse(candidate);
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("answer is not a JSON object");
  return value;
}

let client: Anthropic | null = null;

export async function analysePhoto(body: unknown, ip: string): Promise<PhotoAnswer> {
  const status = photoStatus();
  if (!status.available) return { ok: false, code: "server_setup", message: status.reason };
  if (rateLimited(ip)) return { ok: false, code: "rate_limited", message: "Too many photos from this address. Try again later." };

  const b = (body || {}) as { prompt?: unknown; images?: unknown };
  const images = Array.isArray(b.images) ? b.images : [];
  if (typeof b.prompt !== "string" || b.prompt.length > 20_000 || images.length !== 1) {
    return { ok: false, code: "image_rejected", message: "Send one image and a prompt." };
  }
  const img = images[0] as { mediaType?: unknown; data?: unknown };
  if (typeof img.mediaType !== "string" || !MEDIA_TYPES.has(img.mediaType) || typeof img.data !== "string" || img.data.length > MAX_IMAGE_B64) {
    return { ok: false, code: "image_rejected", message: "The image must be a JPEG, PNG, WebP or GIF under 5 MB." };
  }

  client ??= new Anthropic();
  try {
    // Server-side fallback: if a safety classifier declines, the API retries on a suitable model in the same call.
    const response = await client.beta.messages.create({
      model: MODEL,
      max_tokens: 16000,
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",
      output_config: { effort: "medium" },
      messages: [{
        role: "user",
        content: [
          { type: "image", source: { type: "base64", media_type: img.mediaType as "image/jpeg", data: img.data } },
          { type: "text", text: b.prompt },
        ],
      }],
    });
    if (response.stop_reason === "refusal") return { ok: false, code: "refused", message: "Claude couldn't analyse this image." };
    const text = response.content.flatMap((blk) => (blk.type === "text" ? [blk.text] : [])).join("");
    try {
      return { ok: true, value: parseJsonAnswer(text) };
    } catch {
      return { ok: false, code: "invalid_json", message: "The answer wasn't valid JSON." };
    }
  } catch (err) {
    if (err instanceof Anthropic.AuthenticationError) return { ok: false, code: "server_auth", message: "The server's API key was rejected." };
    if (err instanceof Anthropic.PermissionDeniedError) return { ok: false, code: "server_auth", message: "The server's API key can't use this model." };
    if (err instanceof Anthropic.RateLimitError) return { ok: false, code: "rate_limited", message: "Rate limited." };
    if (err instanceof Anthropic.BadRequestError) {
      console.error("Bad request:", err.message);
      return { ok: false, code: /credit/i.test(err.message) ? "server_billing" : "image_rejected", message: err.message };
    }
    if (err instanceof Anthropic.APIConnectionError) return { ok: false, code: "server_network", message: "Couldn't reach the Claude API." };
    if (err instanceof Anthropic.APIError) {
      console.error("API error:", err.status, err.message);
      return { ok: false, code: "server_error", message: `Claude API error ${err.status}.` };
    }
    throw err;
  }
}

export function clientIp(request: Request) {
  return (request.headers.get("x-forwarded-for") || "").split(",")[0].trim() || "local";
}
