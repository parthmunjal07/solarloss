import { z } from "zod";
import { experimentsSchema, identifier, reviewV1Schema } from "./schemas";
import { adaptV1 } from "./adapters";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const apiUrl = (path: string) => `${base}/api/v1${path}`;
export function reportUrl(id: string) {
  return apiUrl(`/reviews/${encodeURIComponent(identifier.parse(id))}/report`);
}
export async function request<T>(
  url: string,
  schema: z.ZodType<T>,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(url, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: "The experiment identifier is invalid.",
      404: "This review is not available in the API.",
      500: "The API could not load a valid review.",
      503: "The review service is unavailable. Check API configuration and try again.",
    };
    throw new ApiError(
      messages[response.status] ?? "The review request failed.",
      response.status,
    );
  }
  let json: unknown;
  try {
    json = await response.json();
  } catch {
    throw new ApiError(
      "The API returned an invalid results file, rather than JSON.",
      0,
    );
  }
  const result = schema.safeParse(json);
  if (!result.success) {
    console.error(
      "SolarLoss schema mismatch",
      url,
      result.error.issues.map((i) => ({ path: i.path, message: i.message })),
    );
    throw new ApiError(
      "The results file is invalid or uses an unsupported contract. Production reviews require v0.1.0.",
      0,
    );
  }
  return result.data;
}
export const fetchExperiments = (signal?: AbortSignal) =>
  request(apiUrl("/experiments"), experimentsSchema, signal);
export const fetchHealth = (signal?: AbortSignal) =>
  request(
    apiUrl("/health"),
    z.strictObject({ status: z.literal("ok") }),
    signal,
  );
export async function fetchReview(id: string, signal?: AbortSignal) {
  if (!identifier.safeParse(id).success)
    throw new ApiError("The experiment identifier is invalid.", 400);
  const data = await request(
    apiUrl(`/reviews/${encodeURIComponent(id)}`),
    reviewV1Schema,
    signal,
  );
  if (data.experiment.identifier !== id)
    throw new ApiError("The results file belongs to another experiment.", 0);
  return adaptV1(data);
}
export async function fetchResearch(signal?: AbortSignal) {
  if (import.meta.env.DEV) {
    const { adaptResearch } = await import("./research");
    const response = await fetch("/__research-preview", { signal });
    if (!response.ok)
      throw new ApiError(
        "The committed research preview could not be loaded.",
        response.status,
      );
    return adaptResearch(await response.json());
  }
  throw new ApiError(
    "Research previews are available only in development.",
    404,
  );
}
export const shouldRetry = (count: number, error: Error) =>
  count < 2 &&
  (!(error instanceof ApiError) ||
    error.status === 503 ||
    error.status === 500);
