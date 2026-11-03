import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { checkHealth } from "@/lib/api"

type ConnectionState = "idle" | "checking" | "connected" | "error"

export default function App() {
  const [connection, setConnection] = useState<ConnectionState>("idle")
  const [message, setMessage] = useState(
    "Check the connection before starting your reading session.",
  )

  async function handleConnectionCheck() {
    setConnection("checking")
    setMessage("Connecting…")

    try {
      await checkHealth()
      setConnection("connected")
      setMessage("Connected. Your workspace is ready for the next step.")
    } catch {
      setConnection("error")
      setMessage(
        "Could not connect. Make sure the backend is running, then try again.",
      )
    }
  }

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
            Explore your selected chapters through answers linked to the
            passages that support them.
          </p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Workspace connection</CardTitle>
            <CardDescription>
              Confirm that the application can reach its server.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-5">
            <p
              role="status"
              aria-live="polite"
              className={
                connection === "error"
                  ? "text-sm text-destructive"
                  : "text-sm text-muted-foreground"
              }
            >
              {message}
            </p>

            <Button
              onClick={handleConnectionCheck}
              disabled={connection === "checking"}
            >
              {connection === "checking" ? "Checking…" : "Check connection"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}