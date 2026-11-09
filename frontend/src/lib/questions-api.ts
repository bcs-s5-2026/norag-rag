import { z } from "zod"

const citationSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string(),
  index_id: z.string(),
  filename: z.string(),
  content_hash: z.string(),
  start: z.number().int().nonnegative(),
  end: z.number().int().positive(),
  text: z.string(),
  distance: z.number().finite(),
})

const questionResponseSchema = z.object({
  question: z.string(),
  status: z.enum(["answered", "insufficient_evidence"]),
  answer: z.string().min(1),
  citations: z.array(citationSchema).max(20),
  model: z.string().nullable(),
})

export type QuestionResponse = z.infer<typeof questionResponseSchema>

export type QuestionRequest = {
  question: string
  document_ids: string[]
  top_k: number
}

export async function askQuestion(
  request: QuestionRequest,
): Promise<QuestionResponse> {
  let response: Response

  try {
    response = await fetch("/api/questions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(180000),
    })
  } catch {
    throw new Error(
      "The server could not be reached or the answer timed out. " +
        "Check the backend before retrying.",
    )
  }

  const body: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    const error = z.object({ detail: z.string() }).safeParse(body)

    throw new Error(
      error.success
        ? error.data.detail
        : `The question failed (HTTP ${response.status}). Check your inputs.`,
    )
  }

  const parsed = questionResponseSchema.safeParse(body)

  if (!parsed.success) {
    throw new Error("The server returned an unexpected answer format.")
  }

  const result = parsed.data
  const citationIds = result.citations.map((citation) => citation.chunk_id)

  if (
    result.question !== request.question ||
    (result.status === "answered" && result.citations.length === 0) ||
    (result.status === "insufficient_evidence" &&
      result.citations.length !== 0) ||
    new Set(citationIds).size !== citationIds.length ||
    result.citations.some(
      (citation) =>
        !request.document_ids.includes(citation.document_id) ||
        citation.end <= citation.start,
    )
  ) {
    throw new Error("The answer or its references are inconsistent.")
  }

  return result
}