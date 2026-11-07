import { useEffect, useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type StoredDocument,
} from "@/lib/documents-api"

import { IndexControls } from "@/components/index-controls"

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong."
}

export function DocumentPanel() {
  const [documents, setDocuments] = useState<StoredDocument[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [busy, setBusy] = useState(true)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("Loading documents…")

  useEffect(() => {
    let active = true

    listDocuments()
      .then((items) => {
        if (!active) return
        setDocuments(items)
        setLoaded(true)
        setMessage("")
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(errorMessage(reason))
        setMessage("")
      })
      .finally(() => {
        if (active) setBusy(false)
      })

    return () => {
      active = false
    }
  }, [])

  async function refreshDocuments() {
    setBusy(true)
    setError("")
    setMessage("Refreshing documents…")

    try {
      const items = await listDocuments()
      setDocuments(items)
      setSelectedIds((ids) =>
        ids.filter((id) => items.some((item) => item.id === id)),
      )
      setLoaded(true)
      setMessage("Document list refreshed.")
    } catch (reason) {
      setError(errorMessage(reason))
      setMessage("")
    } finally {
      setBusy(false)
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const form = event.currentTarget
    const file = new FormData(form).get("file")

    if (!(file instanceof File) || !file.name) {
      setError("Choose a document first.")
      return
    }

    setBusy(true)
    setError("")
    setMessage("Uploading document…")

    try {
      const uploaded = await uploadDocument(file)
      setDocuments((items) => [uploaded, ...items])
      setMessage(`Uploaded ${uploaded.filename}.`)
      form.reset()
    } catch (reason) {
      setError(errorMessage(reason))
      setMessage("")
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(document: StoredDocument) {
    const confirmed = window.confirm(
      `Delete "${document.filename}" from this workspace?`,
    )

    if (!confirmed) return

    setBusy(true)
    setError("")
    setMessage(`Deleting ${document.filename}…`)

    try {
      await deleteDocument(document.id)
      setDocuments((items) =>
        items.filter((item) => item.id !== document.id),
      )
      setSelectedIds((ids) => ids.filter((id) => id !== document.id))
      setMessage(`Deleted ${document.filename}.`)
    } catch (reason) {
      setError(errorMessage(reason))
      setMessage("")
    } finally {
      setBusy(false)
    }
  }

  function toggleSelection(id: string) {
    setSelectedIds((ids) =>
      ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id],
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your chapters</CardTitle>
        <CardDescription>
          Upload UTF-8 .txt or .md files, up to 2 MiB each.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        <form onSubmit={handleUpload} className="space-y-3">
          <label htmlFor="document-file" className="block text-sm font-medium">
            Choose a document
          </label>

          <input
            id="document-file"
            name="file"
            type="file"
            accept=".txt,.md"
            required
            disabled={busy || !loaded}
            className="block w-full rounded-md border p-3 text-sm file:mr-4 file:cursor-pointer file:font-medium"
          />

          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={busy || !loaded}>
              Upload document
            </Button>

            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={refreshDocuments}
            >
              Refresh list
            </Button>
          </div>
        </form>

        <div aria-live="polite" role="status" className="text-sm">
          {message}
        </div>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="space-y-3">
          <p className="text-sm font-medium">
            {selectedIds.length} of {documents.length} documents selected
          </p>

          <p className="text-sm text-muted-foreground">
            Selection lasts until you reload the page. Documents must be
            indexed before they can support answers.
          </p>

          {loaded && documents.length === 0 && (
            <p className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
              No documents yet. Upload your first chapter above.
            </p>
          )}

          <ul className="space-y-3">
            {documents.map((document) => (
              <li
                key={document.id}
                className="flex flex-wrap items-center justify-between gap-4 rounded-md border p-4"
              >
                <label className="flex min-w-0 flex-1 items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(document.id)}
                    onChange={() => toggleSelection(document.id)}
                    disabled={busy}
                    className="mt-1 size-4 accent-primary"
                  />

                  <span className="min-w-0">
                    <span className="block break-all text-sm font-medium">
                      {document.filename}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {document.character_count.toLocaleString()} characters
                      {" · "}Uploaded
                    </span>
                  </span>
                </label>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  aria-label={`Delete ${document.filename}`}
                  onClick={() => handleDelete(document)}
                >
                  Delete
                </Button>

                <IndexControls
                  documentId={document.id}
                  disabled={busy}
                  onBusyChange={setBusy}
                />
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}