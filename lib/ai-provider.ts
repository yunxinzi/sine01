export type GenerationMode = "Fast" | "Balanced" | "Premium";

export type AiTask =
  | "define"
  | "explore"
  | "generate"
  | "rebuild"
  | "evaluate";

export type AiRequest = {
  task: AiTask;
  mode: GenerationMode;
  input: unknown;
};

export type AiResponse<T = unknown> = {
  ok: boolean;
  provider: "demo" | "openai";
  data: T;
  notes?: string[];
};

/**
 * V0.1 provider boundary.
 *
 * Keep all model credentials and provider calls on the server.
 * The browser should only send structured tasks to server routes.
 * Until a real provider is connected, callers should use deterministic
 * demo data rather than pretending an AI request succeeded.
 */
export async function runAiTask<T>(request: AiRequest): Promise<AiResponse<T>> {
  void request;

  return {
    ok: false,
    provider: "demo",
    data: null as T,
    notes: [
      "Real AI provider is not connected in V0.1.",
      "Add the provider behind a server-only route before enabling AI generation."
    ]
  };
}
