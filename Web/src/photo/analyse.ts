// Browser side of photo analysis: shrink the photo, send it to /api/analyse-photo, map errors to friendly text.

export const ANALYSIS_ERRORS: Record<string, string> = {
  image_rejected: "That file couldn't be read. Try a JPEG, PNG or WebP photo.",
  rate_limited: "Too many requests just now. Wait a moment, then try again.",
  refused: "Claude couldn't analyse this image. Try a different photo of the ring.",
  invalid_json: "The answer couldn't be read as a design. Try again.",
  server_setup: "Photo analysis isn't set up on this server yet. You can still build the design by hand below.",
  server_auth: "The server's Anthropic API key was rejected. The site owner needs to update it.",
  server_billing: "The site's Anthropic API account has no credit left.",
  server_network: "The server couldn't reach Claude. Try again in a moment.",
  server_error: "Claude returned an error. Try again in a moment.",
  offline: "The server isn't answering. Check your connection and try again.",
};

export async function photoStatus(): Promise<{ available: boolean; reason: string }> {
  try {
    const r = await fetch("/api/photo-status", { cache: "no-store" });
    if (!r.ok) return { available: false, reason: "Photo analysis isn't available on this server." };
    return await r.json();
  } catch {
    return { available: false, reason: "Photo analysis isn't available on this server." };
  }
}

async function shrink(file: File, maxSide: number, quality: number): Promise<string> {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale); c.height = Math.round(bmp.height * scale);
  c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", quality);
}

export async function makeThumb(file: File): Promise<string | null> {
  try { return await shrink(file, 240, 0.8); } catch { return null; }
}

export class AnalysisError extends Error {
  constructor(public code: string) { super(code); }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function analyse(file: File, prompt: string, signal: AbortSignal): Promise<any> {
  let data: string;
  try { data = (await shrink(file, 1568, 0.9)).split(",")[1]; } catch { throw new AnalysisError("image_rejected"); }
  let res: Response;
  try {
    res = await fetch("/api/analyse-photo", {
      method: "POST", headers: { "Content-Type": "application/json" }, signal,
      body: JSON.stringify({ prompt, images: [{ mediaType: "image/jpeg", data }] }),
    });
  } catch (e) {
    throw new AnalysisError((e as Error)?.name === "AbortError" ? "cancelled" : "offline");
  }
  const answer = await res.json().catch(() => null);
  if (!answer?.ok) throw new AnalysisError(answer?.code || "server_error");
  return answer.value;
}
