import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { type StoredDocument } from "@/lib/documents-api"
import {
  askQuestion,
  type QuestionResponse,
} from "@/lib/questions-api"

type QuestionPanelProps = {
  documents: StoredDocument[]
  disabled: boolean
  onBusyChange: (busy: boolean) => void
}

type AnswerSnapshot = {
  response: QuestionResponse
  filenames: string[]
  topK: number
}

export function QuestionPanel({
  documents,
  disabled,
  onBusyChange,
}: QuestionPanelProps) {
  const [question, setQuestion] = useState("")
  const [topK, setTopK] = useState("5")
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState("")
  const [snapshot, setSnapshot] = useState<AnswerSnapshot | null>(null)

  const locked = disabled || asking
  const noSelection = documents.length === 0

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedQuestion = question.trim()
    const count = Number(topK)

    setError("")

    if (!trimmedQuestion) {
      setError("Enter a question.")
      return
    }

    if (noSelection) {
      setError("Select at least one document above.")
      return
    }

    if (
      topK.trim() === "" ||
      !Number.isInteger(count) ||
      count < 1 ||
      count > 20
    ) {
      setError("Top-k must be a whole number from 1 to 20.")
      return
    }

    const selectedDocuments = [...documents]

    setSnapshot(null)
    setAsking(true)
    onBusyChange(true)

    try {
      const response = await askQuestion({
        question: trimmedQuestion,
        document_ids: selectedDocuments.map((document) => document.id),
        top_k: count,
      })

      setSnapshot({
        response,
        filenames: selectedDocuments.map((document) => document.filename),
        topK: count,
      })
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The question could not be completed.",
      )
    } finally {
      setAsking(false)
      onBusyChange(false)
    }
  }

  return (
    <section
      aria-labelledby="question-heading"
      className="space-y-5 border-t pt-6"
    >
      <div className="space-y-2">
        <h2 id="question-heading" className="text-xl font-semibold">
          Ask your chapters
        </h2>

        <p className="text-sm text-muted-foreground">
          {noSelection
            ? "Select at least one document using the checkboxes above."
            : `Selected: ${documents.map((document) => document.filename).join(", ")}`}
        </p>

        <p className="text-sm text-muted-foreground">
          Build an index for each selected document before asking.
          Questions use the saved index settings.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="question" className="text-sm font-medium">
            Your question
          </label>

          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What happened when the message arrived?"
            rows={4}
            maxLength={2000}
            required
            disabled={locked}
            className="block w-full rounded-md border bg-background px-3 py-2 text-sm"
          />
        </div>

        <div className="max-w-xs space-y-2">
          <label htmlFor="top-k" className="text-sm font-medium">
            Maximum passages to retrieve (top-k)
          </label>

          <input
            id="top-k"
            type="number"
            min={1}
            max={20}
            step={1}
            required
            value={topK}
            onChange={(event) => setTopK(event.target.value)}
            disabled={locked}
            className="block w-full rounded-md border bg-background px-3 py-2"
          />

          <p className="text-xs text-muted-foreground">
            Applies to your next question. Changing this does not rebuild indexes.
          </p>
        </div>

        <Button type="submit" disabled={locked || noSelection}>
          {asking ? "Finding an answer…" : "Ask question"}
        </Button>
      </form>

      <p role="status" aria-live="polite" className="text-sm">
        {asking
          ? "Retrieving passages and preparing an answer…"
          : snapshot
            ? "Response ready."
            : ""}
      </p>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      {snapshot && (
        <article className="space-y-4 rounded-lg border p-5">
          <div className="space-y-1">
            <h3 className="font-semibold">
              {snapshot.response.status === "answered"
                ? "Answer"
                : "Insufficient evidence"}
            </h3>

            <p className="text-sm font-medium">
              {snapshot.response.question}
            </p>

            <p className="text-xs text-muted-foreground">
              Sources selected: {snapshot.filenames.join(", ")}
              {" · "}Top-k: {snapshot.topK}
            </p>
          </div>

          <p className="whitespace-pre-wrap break-words text-sm leading-7">
            {snapshot.response.answer}
          </p>

          {snapshot.response.citations.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold">
                Supporting passages
              </h4>

              <p className="text-xs text-muted-foreground">
                Open a reference to inspect the exact passage supplied with
                this answer.
              </p>

              {snapshot.response.citations.map((citation, position) => (
                <details
                  key={citation.chunk_id}
                  className="rounded-md border p-3"
                >
                  <summary className="cursor-pointer break-words text-sm font-medium">
                    [{position + 1}] {citation.filename}
                  </summary>

                  <blockquote className="mt-3 whitespace-pre-wrap break-words border-l-2 pl-3 text-sm leading-6">
                    {citation.text}
                  </blockquote>

                  <p className="mt-3 break-all text-xs text-muted-foreground">
                    Chunk: {citation.chunk_id}
                  </p>

                  <p className="mt-1 text-xs text-muted-foreground">
                    Source character range: [{citation.start}, {citation.end})
                  </p>
                </details>
              ))}
            </div>
          )}
        </article>
      )}
    </section>
  )
}