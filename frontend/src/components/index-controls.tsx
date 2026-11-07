import { useEffect, useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  getDocumentIndex,
  rebuildDocumentIndex,
  type DocumentIndex,
} from "@/lib/indexes-api"

type IndexControlsProps = {
  documentId: string
  disabled: boolean
  onBusyChange: (busy: boolean) => void
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "An unexpected error occurred."
}

export function IndexControls({
  documentId,
  disabled,
  onBusyChange,
}: IndexControlsProps) {
  const [index, setIndex] = useState<DocumentIndex | null>(null)
  const [known, setKnown] = useState(false)
  const [loading, setLoading] = useState(true)
  const [building, setBuilding] = useState(false)

  const [chunkSize, setChunkSize] = useState("800")
  const [overlap, setOverlap] = useState("80")

  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true

    getDocumentIndex(documentId)
      .then((result) => {
        if (!active) return

        setIndex(result)
        setKnown(true)

        if (result) {
          setChunkSize(String(result.chunk_size))
          setOverlap(String(result.overlap))
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(errorMessage(reason))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [documentId])

  async function refreshStatus() {
    setLoading(true)
    setError("")
    setMessage("")

    try {
      const result = await getDocumentIndex(documentId)
      setIndex(result)
      setKnown(true)
      setMessage("Index status refreshed.")
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setLoading(false)
    }
  }

  async function handleBuild(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const size = Number(chunkSize)
    const shared = Number(overlap)

    setError("")
    setMessage("")

    if (
      chunkSize.trim() === "" ||
      overlap.trim() === "" ||
      !Number.isInteger(size) ||
      !Number.isInteger(shared) ||
      size < 100 ||
      size > 2000 ||
      shared < 0 ||
      shared >= size
    ) {
      setError(
        "Use a chunk size from 100 to 2000 and an overlap from 0 to chunk size minus 1.",
      )
      return
    }

    setBuilding(true)
    onBusyChange(true)

    try {
      const result = await rebuildDocumentIndex(documentId, {
        chunk_size: size,
        overlap: shared,
      })

      setIndex(result)
      setKnown(true)
      setMessage(`Index saved with ${result.chunk_count} chunks.`)
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setBuilding(false)
      onBusyChange(false)
    }
  }

  const locked = disabled || loading || building

  const settingsChanged =
    index !== null &&
    (Number(chunkSize) !== index.chunk_size ||
      Number(overlap) !== index.overlap)

  return (
    <section
      aria-label="Document indexing"
      className="w-full space-y-3 border-t pt-4"
    >
      <div className="text-sm">
        {loading ? (
          <p>Checking index status…</p>
        ) : !known ? (
          <p>Index status unavailable.</p>
        ) : index ? (
          <p>
            Last confirmed index: {index.chunk_count} chunks · size{" "}
            {index.chunk_size} · overlap {index.overlap}
          </p>
        ) : (
          <p>Not indexed yet.</p>
        )}
      </div>

      <form onSubmit={handleBuild} className="space-y-3">
        <fieldset disabled={locked} className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="block font-medium">
              Chunk size (characters)
            </span>
            <input
              type="number"
              min={100}
              max={2000}
              step={1}
              required
              value={chunkSize}
              onChange={(event) => setChunkSize(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className="block font-medium">
              Overlap (characters)
            </span>
            <input
              type="number"
              min={0}
              max={Math.max(0, Number(chunkSize) - 1)}
              step={1}
              required
              value={overlap}
              onChange={(event) => setOverlap(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2"
            />
          </label>
        </fieldset>

        <p className="text-xs text-muted-foreground">
          {settingsChanged
            ? "These settings differ from the saved index. Rebuild to apply them."
            : "Settings apply when you build the index. Large chunks may exceed the embedding model’s token limit."}
        </p>

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={locked || !known}>
            {building
              ? "Building index…"
              : index
                ? "Rebuild index"
                : "Build index"}
          </Button>

          <Button
            type="button"
            variant="outline"
            disabled={locked}
            onClick={refreshStatus}
          >
            Refresh status
          </Button>
        </div>
      </form>

      <p role="status" aria-live="polite" className="text-sm">
        {building
          ? "Creating embeddings and saving chunks. This may take a moment."
          : message}
      </p>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </section>
  )
}