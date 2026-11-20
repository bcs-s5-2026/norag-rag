import { z } from "zod"

const documentSchema = z.object({
  id: z.string(),
  filename: z.string(),
  content_hash: z.string(),
  character_count: z.number().int().nonnegative(),
  created_at: z.string(),
  status: z.literal("uploaded"),
})

export type StoredDocument = z.infer<typeof documentSchema>

async function request(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  let response: Response

  try {
    response = await fetch(path, {
      ...options,
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    })
  } catch {
    throw new Error(
      "The server could not be reached or the request timed out. Refresh the list before retrying.",
    )
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const parsed = z.object({ detail: z.string() }).safeParse(body)

    throw new Error(
      parsed.success
        ? parsed.data.detail
        : `Request failed (HTTP ${response.status}).`,
    )
  }

  return response
}

export async function listDocuments(): Promise<StoredDocument[]> {
  const response = await request("/api/documents")
  const body: unknown = await response.json()
  const parsed = z.array(documentSchema).safeParse(body)

  if (!parsed.success) {
    throw new Error("The server returned an unexpected document list.")
  }

  return parsed.data
}

export async function uploadDocument(file: File): Promise<StoredDocument> {
  const form = new FormData()
  form.append("file", file)

  const response = await request("/api/documents", {
    method: "POST",
    body: form,
  })

  const body: unknown = await response.json()
  const parsed = documentSchema.safeParse(body)

  if (!parsed.success) {
    throw new Error(
      "The upload response was unexpected. Refresh the document list.",
    )
  }

  return parsed.data
}

export async function deleteDocument(id: string): Promise<void> {
  await request(`/api/documents/${encodeURIComponent(id)}`, {
    method: "DELETE",
  })
}