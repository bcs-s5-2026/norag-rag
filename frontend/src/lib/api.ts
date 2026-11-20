export async function checkHealth(): Promise<void> {
  const response = await fetch("/api/health", {
    signal: AbortSignal.timeout(5000),
    cache: "no-store",
  })

  if (!response.ok) {
    throw new Error(`Server returned HTTP ${response.status}.`)
  }

  const data: unknown = await response.json()

  if (
    typeof data !== "object" ||
    data === null ||
    !("status" in data) ||
    data.status !== "ok"
  ) {
    throw new Error("Server returned an unexpected health response.")
  }
}