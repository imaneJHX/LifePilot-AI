import type {
  ChatMessage,
  ChatResponse,
  Profile,
  ProfileInput,
  Program,
  RealProgramCatalog,
  Recommendations,
  Weights,
} from "./types";

// Empty for the website's Next.js proxy; absolute FastAPI address in Android exports.
const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const timeout = new AbortController();
  const timer = setTimeout(
    () => timeout.abort(),
    path === "/chat" ? 310000 : 20000,
  );
  try {
    const response = await fetch(`${apiBaseUrl}/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
      signal: options?.signal
        ? AbortSignal.any([options.signal, timeout.signal])
        : timeout.signal,
      cache: "no-store",
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const details = data?.error?.details
        ?.map(
          (d: { field: string; message: string }) =>
            `${d.field.replace("body.", "")}: ${d.message}`,
        )
        .join(" ");
      throw new ApiError(
        details ||
          data?.error?.message ||
          "The request could not be completed. Please try again.",
        data?.error?.code ?? "request_failed",
        response.status,
      );
    }
    if (data === null) {
      throw new ApiError(
        "The backend returned an invalid response. Please try again.",
        "invalid_response",
        response.status,
      );
    }
    return data as T;
  } catch (error) {
    if (error instanceof ApiError || options?.signal?.aborted) throw error;
    if (timeout.signal.aborted) {
      throw new ApiError(
        "This request took too long. Please try again.",
        "request_timeout",
        0,
      );
    }
    throw new ApiError(
      "Cannot reach LifePilot. Check that the backend is running and try again.",
      "network_error",
      0,
    );
  } finally {
    clearTimeout(timer);
  }
}
export const api = {
  health: () => request<{ status: string }>("/health"),
  createProfile: (profile: ProfileInput) =>
    request<Profile>("/profile", {
      method: "POST",
      body: JSON.stringify(profile),
    }),
  getProfile: (id: string) =>
    request<Profile>(`/profile/${encodeURIComponent(id)}`),
  programs: (signal?: AbortSignal) =>
    request<Program[]>("/universities", { signal }),
  realPrograms: (signal?: AbortSignal) =>
    request<RealProgramCatalog>("/real-programs", { signal }),
  recommend: (profileId: string, weights?: Weights) =>
    request<Recommendations>("/recommendations", {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, weights }),
    }),
  chat: (messages: ChatMessage[], profileId?: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ messages, profile_id: profileId }),
    }),
};
export const errorMessage = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
