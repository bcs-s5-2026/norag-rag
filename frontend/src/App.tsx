import { DocumentPanel } from "@/components/document-panel"

export default function App() {
  return (
    <main className="min-h-screen bg-background px-6 py-16 text-foreground">
      <div className="mx-auto max-w-3xl space-y-8">
        <header className="space-y-3">
          <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
            A Game of Thrones · Reading workspace
          </p>

          <h1 className="text-4xl font-semibold tracking-tight">
            Ask the chapters.
          </h1>

          <p className="max-w-xl text-muted-foreground">
            Build your collection of chapters, then choose the passages you
            want to explore.
          </p>
        </header>

        <DocumentPanel />
      </div>
    </main>
  )
}