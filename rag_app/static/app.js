const $ = (id) => document.getElementById(id);
let busy = false;
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function status(text, error = false) {
  $("status").textContent = text;
  $("status").className = error ? "error" : "";
}
async function api(path, options) {
  const response = await fetch("/api/" + path, options);
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || "The request failed.");
    error.traceId = data.trace_id; // a failed question still has a trace
    throw error;
  }
  return data;
}
function payload() {
  return {
    document_ids: Array.from(
      document.querySelectorAll(".doc input:checked"),
    ).map((e) => e.value),
    settings: {
      chunk_size: Number($("size").value),
      chunk_overlap: Number($("overlap").value),
      top_k: Number($("topk").value),
    },
  };
}
function retrievalConfig() {
  const retrievers = ["dense", "bm25", "graph"].filter(
    (name) => $("retriever-" + name).checked,
  );
  if (!retrievers.length) throw new Error("Select at least one retriever.");
  return {
    retrievers,
    candidate_depth: Number($("candidate-depth").value),
    rrf_k: Number($("rrf-k").value),
  };
}
function post(body) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
async function run(action) {
  if (busy) return;
  busy = true;
  document.querySelectorAll("button").forEach((e) => (e.disabled = true));
  try {
    await action();
  } catch (error) {
    status(error.message, true);
    if (error.traceId) $("status").append(" ", detailsButton(error.traceId));
  } finally {
    busy = false;
    document.querySelectorAll("button").forEach((e) => (e.disabled = false));
  }
}
async function refresh() {
  const docs = await api("documents");
  const graphs = await api("graphs");
  const old = new Map(
    Array.from(document.querySelectorAll(".doc input")).map((e) => [
      e.value,
      e.checked,
    ]),
  );
  $("documents").replaceChildren();
  $("count").textContent = `${docs.length} sources`;
  for (const doc of docs) {
    const row = node("div", undefined, "doc");
    const label = node("label");
    const check = node("input");
    check.type = "checkbox";
    check.value = doc.id;
    check.checked = old.has(doc.id) ? old.get(doc.id) : true;
    label.append(check, node("span", doc.name));
    const del = node("button", "Delete");
    del.setAttribute("aria-label", `Delete ${doc.name}`);
    del.onclick = () =>
      run(async () => {
        await api("documents/" + doc.id, { method: "DELETE" });
        $("result").replaceChildren(
          node("p", "Source deleted. Ask again to refresh evidence."),
        );
        await refresh();
        status("Document and its indexed passages deleted.");
      });
    const graph = graphs[doc.id];
    row.append(label);
    if (!graph) {
      const build = node("button", "Build graph");
      build.type = "button";
      build.title = "Extract a concept graph from this document (one model call per passage)";
      build.onclick = () =>
        run(async () => {
          status("Building the concept graph… one model call per passage.");
          const info = await api(`documents/${doc.id}/graph`, post({}));
          await refresh();
          status(`Concept graph built: ${info.concepts} concepts, ${info.links} links.`);
        });
      row.append(build);
    }
    row.append(del);
    $("documents").append(row);
  }
  await loadConceptSources(graphs);
}
$("upload").onsubmit = (event) => {
  event.preventDefault();
  run(async () => {
    status("Uploading source…");
    const form = new FormData();
    form.append("file", $("file").files[0]);
    const data = await api("documents", { method: "POST", body: form });
    await refresh();
    $("file").value = "";
    const g = data.graph || {};
    const graphNote = {
      built: ` Concept graph built: ${g.concepts} concepts, ${g.links} links${g.complete ? "" : " (partial: some passages failed)"}.`,
      exists: " Its concept graph already exists.",
      skipped: " No concept graph: " + g.reason,
      too_large: " No concept graph yet: " + g.reason,
      failed: " The concept graph could not be built: " + g.reason + " Sources still work with the other search methods.",
    }[g.status] || "";
    status(
      (data.duplicate
        ? "This content is already in your library."
        : "Source added. It will be indexed on your next question.") + graphNote,
    );
  });
};
$("index").onclick = () =>
  run(async () => {
    status("Preparing documents… The first run may download the embedding model.");
    const data = await api("index", post(payload()));
    status(
      `Documents ready: ${data.chunks} passages across ${data.documents} documents.`,
    );
    const latest = await api("traces?kind=indexing&limit=1");
    if (latest.length) $("status").append(" ", detailsButton(latest[0].id));
  });
$("ask").onsubmit = (event) => {
  event.preventDefault();
  run(async () => {
    $("result").replaceChildren(
      node("p", "Retrieving evidence and preparing an answer…", "hint"),
    );
    status(
      "Working… Indexing new sources, retrieving passages, then asking the model.",
    );
    let data;
    try {
      data = await api(
        "ask",
        post({ ...payload(), question: $("question").value, retrieval: retrievalConfig() }),
      );
    } catch (error) {
      // Never leave "preparing an answer…" on screen after a failure.
      $("result").replaceChildren(
        node("p", "NO ANSWER THIS TIME", "eyebrow"),
        node("p", "Nothing is shown because the request failed or the answer could not be checked. The message above says why; you can try again."),
      );
      throw error;
    }
    const result = $("result");
    result.replaceChildren(
      node(
        "p",
        data.answerable ? "GENERATED ANSWER" : "INSUFFICIENT EVIDENCE",
        "eyebrow",
      ),
      node("p", data.answer),
      detailsButton(data.trace_id),
    );
    if (data.references.length)
      result.append(node("h2", "Supporting references"));
    for (const ref of data.references) result.append(reference(ref));
    const all = node("details", undefined, "reference");
    all.append(
      node(
        "summary",
        `Inspect all ${data.retrieved.length} retrieved passages`,
      ),
    );
    for (const ref of data.retrieved) all.append(reference(ref));
    result.append(all);
    if (data.graph_trace) renderGraph(result, data.graph_trace, data.references);
    status("Answer ready. Open a passage to check the evidence, or Details to see each step.");
  });
};
function reference(ref) {
  const detail = node("details", undefined, "reference");
  detail.append(
    node(
      "summary",
      `${ref.name} · line ${ref.line} · characters ${ref.start}–${ref.end}`,
    ),
    node("p", ref.text),
  );
  if (ref.origins) {
    detail.append(node("small", Object.entries(ref.origins)
      .map(([name, info]) => `${name}: rank ${info.rank}, raw score ${Number(info.raw_score).toFixed(3)}`)
      .join(" · ")));
    detail.append(node("p", `Fused rank ${ref.fused_rank} · RRF ${Number(ref.rrf_score).toFixed(6)} (not a confidence score)`));
  } else if (typeof ref.similarity === "number") {
    detail.append(node("small", `Cosine similarity ${ref.similarity.toFixed(3)} · not a confidence score`));
  }
  return detail;
}
function renderGraph(host, trace, references = []) {
  const section = node("section");
  section.append(node("h3", "Graph evidence paths"));
  if (!trace.complete) {
    const c = trace.coverage || {};
    const text = trace.note
      ? trace.note
      : c.valid_chunks !== undefined
        ? `Partial extraction: ${c.valid_chunks}/${c.total_chunks} chunks validated.`
        : "Partial extraction: some passages could not be read by the model.";
    section.append(node("p", text + " Missing graph facts can affect retrieval.", "hint"));
  }
  section.append(node("p", "Question entities: " + (trace.matched_entities.map((e) => `${e.label} (${e.matched_by})`).join(", ") || "none")));
  if (trace.reason) section.append(node("p", trace.reason));
  const cited = new Set(references.flatMap((r) => r.origins?.graph?.path_ids || []));
  const paths = cited.size ? trace.paths.filter((p) => cited.has(p.id)) : trace.paths;
  section.append(node("p", cited.size ? "Paths attached to cited references:" : "Retrieved paths (not a claim that an answer used every path):"));
  const chunks = new Map((trace.chunks || []).map((c) => [c.id, c]));
  for (const path of paths.slice(0, 20)) {
    const view = node("details", undefined, "graph-path");
    view.append(node("summary", path.nodes.map((n) => n.label).join(" → ")));
    const labels = new Map(path.nodes.map((n) => [n.id, n.label]));
    for (const edge of path.edges) {
      view.append(node("p", `${labels.get(edge.subject_id)} — ${edge.relation} → ${labels.get(edge.object_id)} (walk ${edge.direction})`));
      if (edge.condition_quote) view.append(node("p", "Condition: " + edge.condition_quote));
      for (const proof of edge.evidence) {
        const passage = node("details");
        const rank = trace.fused_chunk_ranks?.[proof.chunk_id];
        passage.append(node("summary", `${proof.source_document} · characters ${proof.quote_start}–${proof.quote_end} · ${rank ? "fused rank " + rank : "outside final fused selection"}`));
        passage.append(node("blockquote", proof.quote));
        const chunk = chunks.get(proof.chunk_id);
        if (chunk) passage.append(node("pre", chunk.text));
        view.append(passage);
      }
    }
    if (!path.edges.length) {
      view.append(node("p", "Direct entity match; source chunks:"));
      for (const id of path.chunk_ids) {
        const chunk = chunks.get(id);
        if (chunk) { const passage = node("details"); passage.append(node("summary", `${chunk.name} · ${id}`), node("pre", chunk.text)); view.append(passage); }
      }
    }
    section.append(view);
  }
  if (paths.length > 20) section.append(node("p", `Showing 20 of ${paths.length} paths.`));
  if (trace.traversal_limit_reached) section.append(node("p", "The bounded traversal reached its exploration limit."));
  host.append(section);
}
refresh().catch((e) => status(e.message, true));
api("evaluation")
  .then((data) => {
    const host = $("evaluation");
    if (data.hit_at_k !== undefined) {
      host.append(
        node(
          "h3",
          `Hit@${data.settings.top_k}: ${(data.hit_at_k * 100).toFixed(1)}%`,
        ),
        node(
          "p",
          `${data.hits} of ${data.answerable_count} answerable questions retrieved the expected passage. ${data.unanswerable_count} unanswerable questions excluded from this metric.`,
          "hint",
        ),
      );
    }
    const details = node("details");
    details.append(
      node("summary", "Dataset, settings and per-question results"),
      node("pre", JSON.stringify(data, null, 2)),
    );
    host.append(details);
  })
  .catch((e) => ($("evaluation").textContent = e.message));

// C7 evaluation and Words share the existing selected sources and settings.
function showTab(id) {
  document.querySelectorAll(".tab-view").forEach((view) => {
    view.hidden = view.id !== id;
  });
  document
    .querySelectorAll("[data-tab]")
    .forEach((tab) =>
      tab.setAttribute("aria-pressed", String(tab.dataset.tab === id)),
    );
}
document.querySelectorAll("[data-tab]").forEach((button) => {
  button.onclick = () => showTab(button.dataset.tab);
});
api("question-sets")
  .then((sets) => {
    for (const [corpus, questions] of Object.entries(sets)) {
      for (const q of questions) {
        const option = node("option", `${corpus} / ${q.id}: ${q.question}`);
        option.value = q.question;
        $("word-question").append(option);
      }
    }
  })
  .catch((e) => status(e.message, true));
$("word-question").onchange = () => {
  $("words-question").value = $("word-question").value;
  $("words-mode").value = "question";
};
// Upload one of the two course corpora, select only its documents and
// switch to the search methods that measured best for it (see REPORT.md).
async function loadCorpus(name) {
  const docs = await api("corpora/" + name, post({}));
  await refresh();
  const ids = new Set(docs.map((d) => d.id));
  document.querySelectorAll(".doc input").forEach((c) => {
    c.checked = ids.has(c.value);
  });
  const kestrel = name === "kestrel";
  $("retriever-dense").checked = kestrel;
  $("retriever-bm25").checked = true;
  $("retriever-graph").checked = kestrel;
  return kestrel;
}
$("load-demo").onclick = () =>
  run(async () => {
    await loadCorpus("kestrel");
    $("question").value = "Error KST-5031 happened on the last two scheduled reports. Which team should support contact, and where?";
    status("Demo documents loaded and selected. A sample question is ready: press “Find an answer”.");
  });
$("load-corpus").onclick = () =>
  run(async () => {
    const kestrel = await loadCorpus($("eval-corpus").value);
    status(`Corpus loaded. Measured default: ${kestrel ? "dense + BM25 + graph (Recall@5 0.79, two-hop 0.89)" : "BM25 (Recall@5 0.92)"}. You can change the retrievers above.`);
  });
function downloadJSON(data, filename) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const link = node("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function showRun(runId, result) {
  $("saved-run").value = runId;
  localStorage.setItem("rag-last-evaluation", runId);
  const host = $("eval-results");
  host.replaceChildren();
  host.append(node("p", `Saved run: ${runId}`));
  const download = node("button", "Download saved results");
  download.onclick = () =>
    run(async () =>
      downloadJSON(
        await api("evaluations/" + runId),
        `${result.corpus}-${runId}.json`,
      ),
    );
  host.append(
    download,
    node("h3", "Overall and per-type metrics"),
    node(
      "pre",
      JSON.stringify(
        {
          settings: result.settings,
          retrieval: result.retrieval,
          question_set: result.question_set,
          overall: result.overall,
          by_type: result.by_type,
        },
        null,
        2,
      ),
    ),
  );
  const rules = node("details");
  rules.append(
    node("summary", "Grading rules (read before grading)"),
    node("pre", JSON.stringify(result.grading_rules, null, 2)),
  );
  host.append(rules);
  for (const row of result.results) {
    const detail = node("details");
    detail.append(node("summary", `${row.id} / ${row.type}: ${row.question}`));
    detail.append(node("p", `Expected: ${row.expected_answer}`));
    if (row.retrieval_seconds !== undefined)
      detail.append(node("p", `Retrieval ${(row.retrieval_seconds * 1000).toFixed(2)} ms · LLM calls ${row.llm_calls}`));
    if (row.graph_trace) renderGraph(detail, row.graph_trace, row.response?.references || []);
    detail.append(
      node(
        "pre",
        JSON.stringify(
          {
            hits: row.hits,
            quote_recall: row.quote_recall,
            evidence: row.evidence,
          },
          null,
          2,
        ),
      ),
    );
    if (row.response || row.no_context_answer !== undefined) {
      if (row.response) {
        detail.append(node("p", `Generated: ${row.response.answer}`));
        for (const ref of row.response.references)
          detail.append(reference(ref));
      }
      const grading = node("form");
      const gradeLabel = node("label", "Grade");
      const grade = node("select");
      for (const value of ["", "correct", "partial", "wrong", "unsupported"]) {
        const op = node("option", value || "Choose after review");
        op.value = value;
        grade.append(op);
      }
      grade.value = row.grade || "";
      grade.required = !!row.response;
      grade.disabled = !row.response;
      gradeLabel.append(grade);
      const reviewerLabel = node("label", "Reviewer");
      const reviewer = node("input");
      reviewer.required = true;
      reviewer.maxLength = 100;
      reviewer.value = row.reviewer || "";
      reviewerLabel.append(reviewer);
      const noteLabel = node(
        "label",
        "Notes: supporting facts; retrieval or generation failure",
      );
      const notes = node("textarea");
      notes.required = true;
      notes.maxLength = 3000;
      notes.value = row.grade_notes || "";
      noteLabel.append(notes);
      const ncLabel = node(
        "label",
        "No-context answer supplies expected facts?",
      );
      const nc = node("select");
      for (const [value, label] of [
        ["", "Not reviewed"],
        ["true", "Yes — flag prior knowledge"],
        ["false", "No"],
      ]) {
        const op = node("option", label);
        op.value = value;
        nc.append(op);
      }
      nc.value =
        row.no_context_correct === null ? "" : String(row.no_context_correct);
      nc.disabled = row.no_context_answer === undefined;
      nc.required = row.no_context_answer !== undefined;
      ncLabel.append(nc);
      const save = node("button", "Save human grade");
      save.type = "submit";
      grading.append(gradeLabel, reviewerLabel, noteLabel, ncLabel, save);
      grading.onsubmit = (e) => {
        e.preventDefault();
        run(async () => {
          await api(
            `evaluations/${runId}/grades`,
            post({
              question_id: row.id,
              grade: grade.value || null,
              notes: notes.value,
              reviewer: reviewer.value,
              no_context_correct: nc.value === "" ? null : nc.value === "true",
            }),
          );
          status("Grade saved to results file.");
        });
      };
      detail.append(grading);
    }
    if (row.generation_error)
      detail.append(node("p", row.generation_error, "error"));
    if (row.no_context_answer !== undefined)
      detail.append(node("p", `Without retrieval: ${row.no_context_answer}`));
    if (row.no_context_error)
      detail.append(node("p", row.no_context_error, "error"));
    const passages = node("details");
    passages.append(node("summary", "All retrieved passages"));
    for (const ref of row.retrieved) passages.append(reference(ref));
    detail.append(passages);
    host.append(detail);
  }
}
$("evaluate").onclick = () =>
  run(async () => {
    status(
      "Running evaluation… Hosted generation, if selected, may take several minutes.",
    );
    const retrieval = retrievalConfig();
    const hosted = $("eval-answers").checked || $("eval-no-context").checked;
    if (hosted && (retrieval.retrievers.join() !== "dense" || $("eval-question-set").value !== "v2"))
      throw new Error("Hosted review supports original dense V2 only. Clear hosted options for a V3 retrieval evaluation.");
    const body = {corpus: $("eval-corpus").value, settings: payload().settings};
    const data = hosted ? await api("evaluations", post({...body, answers: $("eval-answers").checked, no_context: $("eval-no-context").checked}))
      : await api("evaluations/v3", post({...body, retrieval, question_set: $("eval-question-set").value}));
    showRun(data.run_id, data.result);
    status("Evaluation saved. Review per-question results and any errors.");
  });
$("saved-run").value = localStorage.getItem("rag-last-evaluation") || "";
$("restore-run").onclick = () =>
  run(async () => {
    const id = $("saved-run").value;
    showRun(id, await api("evaluations/" + encodeURIComponent(id)));
    status("Saved evaluation opened.");
  });
$("analyze").onclick = () =>
  run(async () => {
    const data = await api(
      "words",
      post({
        ...payload(),
        question:
          $("words-mode").value === "question" ? $("words-question").value : "",
        word: $("words-mode").value === "corpus" ? $("word-query").value : "",
      }),
    );
    const host = $("word-results");
    host.replaceChildren(
      node("p", `${data.chunk_count} chunks. ${data.counting}`),
    );
    for (const word of data.words) {
      const detail = node("details");
      detail.append(
        node(
          "summary",
          `${word.word}: ${word.present ? `${word.occurrences} occurrences in ${word.chunks} chunks` : "absent from corpus"}`,
        ),
      );
      for (const passage of word.passages) {
        const item = node("details");
        item.append(
          node(
            "summary",
            `${passage.name}: ${passage.start}–${passage.end} / ${passage.count} occurrences`,
          ),
          node("p", passage.text),
        );
        detail.append(item);
      }
      host.append(detail);
    }
    if ($("words-mode").value === "corpus") {
      const table = node("table");
      const head = node("tr");
      for (const title of ["Word", "Occurrences", "Chunks"])
        head.append(node("th", title));
      table.append(head);
      for (const row of data.vocabulary) {
        const tr = node("tr");
        const cell = node("td");
        const link = node("button", row.word, "secondary");
        link.onclick = () => {
          $("word-query").value = row.word;
          $("analyze").click();
        };
        cell.append(link);
        tr.append(
          cell,
          node("td", String(row.occurrences)),
          node("td", String(row.chunks)),
        );
        table.append(tr);
      }
      host.append(table);
    }
    status("Word analysis ready.");
  });

api("measured-runs")
  .then((names) => {
    for (const name of names) {
      const option = node("option", name);
      option.value = name;
      $("measured-run").append(option);
    }
  })
  .catch((e) => status(e.message, true));
$("open-measured-run").onclick = () =>
  run(async () => {
    const data = await api(
      "measured-runs/" + encodeURIComponent($("measured-run").value),
      post({}),
    );
    showRun(data.run_id, data.result);
    status(
      "Measured run copied to local review. Save grades and download the reviewed JSON.",
    );
  });

// ---- V4 Part A: open the trace of an answer, an indexing run or a concept lookup.
const STEP_NAMES = {
  dense: "Search by meaning (dense embeddings)",
  bm25: "Search by exact words (BM25)",
  graph: "Search the concept graph",
  fusion: "Merge the rankings (RRF)",
  redact: "Hide personal data before the LLM call",
  generate: "Write the answer (LLM call)",
  validate: "Check the answer format and citations",
  embed_document: "Split and embed a document",
  bm25_index: "Build the exact-word index",
  load_graph: "Load the concept graph",
  neighborhood: "Collect links and source chunks",
};
const TRACE_TITLES = {
  question: "What happened for this question",
  indexing: "What happened in this indexing run",
  concept: "What happened for this concept lookup",
};
function detailsButton(traceId) {
  const button = node("button", "Details", "secondary details-button");
  button.type = "button";
  button.onclick = () => showTrace(traceId).catch((e) => status(e.message, true));
  return button;
}
// Document ids are 64-character hashes: keep the first 8 so chunk ids stay readable.
function shorten(value) {
  return String(value).replace(/[0-9a-f]{64}/g, (hash) => hash.slice(0, 8) + "…");
}
function describe(attributes) {
  return Object.entries(attributes)
    .map(([key, value]) => {
      if (key === "results")
        // Fused ranking: one line per chunk, with the rank each search method gave it.
        value = value.map((r) => `\n  #${r.fused_rank} ${r.chunk_id} (found by ${Object.entries(r.found_by).map(([name, rank]) => `${name} #${rank}`).join(", ")})`).join("");
      else if (Array.isArray(value) && value.every((v) => typeof v !== "object"))
        value = value.join(", ") || "none";
      else if (value !== null && typeof value === "object") value = JSON.stringify(value);
      return `${key.replaceAll("_", " ")}: ${shorten(value)}`;
    })
    .join("\n");
}
function traceSummary(trace) {
  const parts = [`Outcome: ${trace.outcome}`, `${trace.duration_ms} ms`, `LLM calls: ${trace.llm_calls}`];
  if (trace.input_tokens !== null)
    parts.push(`tokens: ${trace.input_tokens} in / ${trace.output_tokens} out`);
  if (trace.cost_usd !== null) parts.push(`cost: $${trace.cost_usd.toFixed(6)}`);
  return parts.join(" · ");
}
async function showTrace(traceId) {
  const trace = await api("traces/" + encodeURIComponent(traceId));
  const body = $("trace-body");
  const title = node("h2", TRACE_TITLES[trace.kind] || "Trace");
  title.id = "trace-title";
  body.replaceChildren(title, node("p", traceSummary(trace)));
  if (trace.error) body.append(node("p", trace.error, "error"));
  if (trace.attributes.question)
    body.append(node("p", "Question as stored (personal data replaced): " + trace.attributes.question));
  const table = node("table");
  const head = node("tr");
  for (const name of ["Step", "Time", "What happened"]) head.append(node("th", name));
  table.append(head);
  for (const span of trace.spans) {
    const row = node("tr");
    const what = node("td", describe(span.attributes), "trace-what");
    if (span.status === "error") what.prepend(node("strong", `Failed (${span.error}). `));
    row.append(node("td", STEP_NAMES[span.name] || span.name), node("td", `${span.duration_ms} ms`), what);
    table.append(row);
  }
  body.append(table);
  if (!trace.spans.length) body.append(node("p", "No step was needed (nothing to do).", "hint"));
  body.append(node("p", `Trace ${trace.id} · ${new Date(trace.started_at).toLocaleString()} · stored only on this computer for 30 days. It contains chunk ids, never document text.`, "hint"));
  const raw = node("details");
  raw.append(node("summary", "Raw trace (JSON)"), node("pre", JSON.stringify(trace, null, 2)));
  body.append(raw);
  if (!$("trace-dialog").open) $("trace-dialog").showModal();
}
$("recent-traces").onclick = async () => {
  try {
    const traces = await api("traces?limit=30");
    const title = node("h2", "Recent activity");
    title.id = "trace-title";
    $("trace-body").replaceChildren(title);
    if (!traces.length) $("trace-body").append(node("p", "Nothing recorded yet. Ask a question first.", "hint"));
    for (const trace of traces) {
      const label = trace.attributes.question || trace.attributes.label || `${trace.attributes.documents ?? 0} documents`;
      const line = node("p");
      line.append(detailsButton(trace.id), ` ${new Date(trace.started_at).toLocaleString()} · ${trace.kind} · ${trace.outcome} · ${label}`);
      $("trace-body").append(line);
    }
    if (!$("trace-dialog").open) $("trace-dialog").showModal();
  } catch (error) {
    status(error.message, true);
  }
};

// ---- V4 Part B: concept map explorer (read-only view of the V3 Kestrel graph).
const SVG = "http://www.w3.org/2000/svg";
function svg(tag, attributes, text) {
  const el = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, value);
  if (text !== undefined) el.textContent = text;
  return el;
}
function sourcePassage(proof) {
  const detail = node("details", undefined, "reference");
  detail.append(
    node("summary", `${proof.document} · line ${proof.line} · characters ${proof.quote_start}–${proof.quote_end}`),
    node("blockquote", proof.quote),
  );
  const chunk = node("details");
  chunk.append(node("summary", "Open the full source chunk"), node("pre", proof.chunk_text));
  detail.append(chunk);
  return detail;
}
// The selected concept in the centre, one neighbour per link on an ellipse around it.
function drawNeighborhood(data) {
  const picture = svg("svg", { viewBox: "0 0 720 440", role: "img", "aria-label": `Links of ${data.concept.label}` });
  const cx = 360, cy = 220;
  data.links.forEach((link, i) => {
    const angle = (2 * Math.PI * i) / data.links.length - Math.PI / 2;
    const x = cx + 270 * Math.cos(angle), y = cy + 170 * Math.sin(angle);
    picture.append(svg("line", { x1: cx, y1: cy, x2: x, y2: y, class: "edge" }));
    const arrow = link.direction === "out" ? `${link.relation} →` : `← ${link.relation}`;
    picture.append(svg("text", { x: (cx + x) / 2, y: (cy + y) / 2 - 4, class: "edge-label" }, arrow));
    const neighbour = svg("g", { class: "concept", tabindex: 0, role: "button" });
    neighbour.append(
      svg("circle", { cx: x, cy: y, r: 9 }),
      svg("text", { x, y: y + (y < cy ? -14 : 24) }, `${link.other.label} (${link.other.type})`),
    );
    neighbour.onclick = () => openConcept(link.other.id);
    neighbour.onkeydown = (event) => { if (event.key === "Enter") openConcept(link.other.id); };
    picture.append(neighbour);
  });
  const centre = svg("g", { class: "concept centre" });
  centre.append(svg("circle", { cx, cy, r: 13 }), svg("text", { x: cx, y: cy + 30 }, data.concept.label));
  picture.append(centre);
  return picture;
}
async function openConcept(id) {
  try {
    const data = await api("concepts/" + encodeURIComponent(id) + conceptQuery());
    $("concept-select").value = id;
    $("concept-map").replaceChildren(drawNeighborhood(data));
    const detail = $("concept-detail");
    const ask = node("button", "Ask a question about this concept");
    ask.type = "button";
    ask.onclick = () =>
      run(async () => {
        if (!$("concept-source").value) await loadCorpus("kestrel"); // the demo graph only covers the Kestrel documents
        $("question").value = `What do the documents say about ${data.concept.label}?`;
        showTab("ask-view");
        $("question").focus();
        status("Question prepared from the concept map. Edit it if you like, then press “Find an answer”.");
      });
    detail.replaceChildren(
      node("h3", `${data.concept.label} — ${data.concept.type}`),
      ask, " ", detailsButton(data.trace_id),
      node("h3", `Linked concepts (${data.links.length})`),
    );
    if (!data.links.length) detail.append(node("p", "No link was extracted for this concept.", "hint"));
    for (const link of data.links) {
      const from = link.direction === "out" ? data.concept.label : link.other.label;
      const to = link.direction === "out" ? link.other.label : data.concept.label;
      const view = node("details");
      view.append(node("summary", `${from} — ${link.relation} → ${to}`));
      if (link.condition) view.append(node("p", "Condition: " + link.condition));
      for (const proof of link.evidence) view.append(sourcePassage(proof));
      detail.append(view);
    }
    detail.append(node("h3", `Where the documents mention it (${data.mentions.length})`));
    for (const proof of data.mentions) detail.append(sourcePassage(proof));
  } catch (error) {
    status(error.message, true);
    if (error.traceId) $("status").append(" ", detailsButton(error.traceId));
  }
}
function conceptQuery() {
  const source = $("concept-source").value;
  return source ? "?documents=" + encodeURIComponent(source) : "";
}
async function loadConceptSources(graphs) {
  const select = $("concept-source");
  const keep = select.value;
  select.replaceChildren(node("option", "Kestrel demo documents"));
  select.firstChild.value = "";
  for (const [id, info] of Object.entries(graphs)) {
    const option = node("option", `${info.name} (${info.concepts} concepts)`);
    option.value = id;
    select.append(option);
  }
  select.value = graphs[keep] ? keep : "";
}
async function loadConcepts() {
  const select = $("concept-select");
  select.replaceChildren(node("option", "Choose a concept…"));
  select.firstChild.value = "";
  $("concept-map").replaceChildren();
  $("concept-detail").replaceChildren();
  try {
    const concepts = await api("concepts" + conceptQuery());
    const groups = new Map();
    for (const concept of concepts) {
      if (!groups.has(concept.type)) {
        const group = node("optgroup");
        group.label = concept.type;
        groups.set(concept.type, group);
        select.append(group);
      }
      const option = node("option", `${concept.label} (${concept.links} links)`);
      option.value = concept.id;
      groups.get(concept.type).append(option);
    }
  } catch (error) {
    $("concept-detail").replaceChildren(node("p", error.message, "error"));
  }
}
$("concept-source").onchange = loadConcepts;
loadConcepts();
$("concept-select").onchange = () => {
  if ($("concept-select").value) openConcept($("concept-select").value);
};
