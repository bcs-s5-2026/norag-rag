# My Understanding and Learning Experience — Testing and Extending the RAG Project

**Student:** Makuochukwu Okoene (Makuo)  
**Course:** AI Systems Integration and Operations  
**Professor:** Denis Amselem  
**Project:** norag-rag  
**Team:** Feras Michael and Makuochukwu Okoene

## 1. Introduction — Joining as a Tester

I want to start this report with an honest note about my role.

Feras built V1 to V4 of the application, with the help of AI coding tools. Our main report says so.

My part started at the end. I took the finished project, cloned it on my own computer, and tried to use it like a stranger would.

My first question was simple: if someone who did not write this code follows the README, does it work, and can they trust the answers?

I did not know the answer. That is why I wrote down everything I saw in ten tests, called T1 to T10, with screenshots.

Testing from the outside taught me a lot, because I could not rely on knowing how the code worked. I had to rely on what the application showed me.

Later, the testing led me to fix and add some things on my branch. I also used an AI assistant (Claude) to help me debug, to write the fixes and the tests, and to draft my testing report. I ran everything myself and checked it on my own machine before committing.

## 2. My First Test Failed — Setup and Reproducibility

I followed the README on my Mac and ran the tests.

28 tests failed and 146 passed.

The errors said `NameError: name 'nn' is not defined` and "Embedding model unavailable".

At first, I thought the project was broken. After investigating, I understood the problem was my computer.

I have an Intel MacBook Pro. Intel Macs can only install PyTorch 2.2.2. The README did not pin the package versions, so pip downloaded the newest `sentence-transformers` and `transformers`. Those need PyTorch 2.6 or newer.

I had also been running everything outside a virtual environment, on my global Python.

What fixed it:

1. Install Python 3.12 with pyenv.
2. Create a fresh virtual environment.
3. Pin older libraries: `numpy<2`, `sentence-transformers<4`, `transformers<4.50` and `huggingface-hub<1.0`.

After that, 174 tests passed.

I added a short Intel Mac note to the README, so the next person does not lose an hour like I did.

The lesson for me was that a project is not finished when it works on the author's machine. It is finished when someone else can run it.

## 3. What I Saw When I Used It

### References I can check

I asked "What does KST-5031 mean?"

The answer was short: the error means "Scheduled report not delivered". The report was generated but the e-mail was not sent, and the error comes from postroom.

What I liked most is that every answer comes with its references. Each one names the file, the line and the exact character range. I could open the passage and read what the answer was built from.

That means I could check the answer myself instead of trusting it.

Under each passage, the application also shows how the passage was ranked. For this question, the chunk was rank 1 for BM25, rank 1 for dense and rank 1 for the graph.

The fused score was 0.049180.

Later I realised this number is simply three equal contributions. In reciprocal rank fusion, each retriever gives $\frac{1}{60 + \text{rank}}$, and for rank 1 that is $\frac{1}{61}$. Three of them make $\frac{3}{61} = 0.04918$.

The application says in plain words that this is not a confidence score. I appreciated that honesty.

### A surprise about BM25

I ran the same question with each search method on its own.

Dense put the right passage at rank 1. The graph also put it at rank 1.

BM25 put it at rank 5, behind three passages that were just the beginnings of other files.

I expected the opposite. I thought exact words would win on an exact code like KST-5031.

I did not hide this result. I recorded it as a finding. Our report on the retrieval results said that the best method depends on the documents and the questions, and this was a small example of it.

### The question that needs two steps

My second question was: "Error KST-5031 happened on the last two scheduled reports. Which team should support contact, and where?"

This needs two hops. The error points to postroom, and postroom is owned by a team.

Dense search and BM25 found the error passage, but not the passage that says who owns postroom. Their answers said to escalate "to the team that owns postroom" and never named the team.

With the graph, the answer named the Messaging team. The graph walked from KST-5031 to postroom, then to Messaging, then to #oncall-messaging. It cited the service-catalog passage that the other two methods missed.

In the trace, that passage was rank 16 for BM25 and rank 20 for dense, but rank 2 for the graph. Reciprocal rank fusion added the three contributions:

\[
\frac{1}{60+16} + \frac{1}{60+20} + \frac{1}{60+2} \approx 0.0418
\]

Without the graph it would only have scored about 0.0257, and it would not have reached the top five.

This was the clearest result of all my tests. The graph is what answers questions that need two steps.

### The Details view

Every answer has a Details button. It shows what the application did, step by step: dense search, BM25, graph, the merge, hiding personal data, the model call and the final check. Each step has its time in milliseconds.

I noticed that three searches ran but only one model call was made. The merge is simple arithmetic, so it costs nothing. That call used 3407 tokens in and 203 out, for about $0.0015.

The first question took about 3 seconds, and later ones about 1 second. I think the first run was loading the embedding model, but I did not check this, so I only treat it as a guess.

## 4. When the Answer Is Not in the Documents

I asked "what is north-star metrics", which is not in the documents.

The application did not make something up. It answered that the selected documents do not provide enough evidence, and it cited nothing.

The trace showed what happened behind that answer. The outcome was "abstained" and the graph found nothing, which was correct.

But dense search and BM25 still returned 20 candidates each, so five unrelated passages were sent to the model anyway. That cost one model call, with 2617 tokens in, just to say "no".

So the abstention works, but the retrieval has no relevance cut-off.

I do not call this a bug. It is an idea for improvement: a minimum score would let the application skip the model call when nothing relevant was found.

This helped me understand a point from the course. A prompt can ask the model to say "I do not know", but the code makes sure that an answer without evidence is rejected. Abstaining correctly is not the same as abstaining cheaply.

## 5. Personal Data — I Checked the Claim Myself

The footer of the application says the trace is stored only on my computer and contains chunk ids, never document text.

I did not want to just believe that.

I used dummy details: the email `sam.student@example.org` and the phone `+33 6 12 34 56 78`, inside a question about refunds.

What I saw:

- The question stored in the trace read "My email is [EMAIL_1] and my phone is [PHONE_1]". The real values were replaced before anything was saved or sent.
- The step that hides personal data counted 2 emails and 1 phone. The second email came from the documents, so the application hides contact details in the documents too, not only in my question.
- The answer was still correct. The application put the real address back locally after the model replied.

Then I searched the saved traces file for my dummy data. Both searches returned 0.

So the claim was true. I could prove it instead of just trusting it.

But I also found the limit: only emails and phones are hidden. A person's name is not. In another test, the answer contained a name from the documents, and it went to the model as plain text. I did not test a name inside my own question.

Redaction is partial protection, not anonymisation. Because the application keeps a way to restore the real values, the data is pseudonymised, not anonymous.

## 6. Where It Broke, and What I Built

### The failure

The most important test was the last one, T10.

I wrote a small file about a made-up project and uploaded it. With the default search methods, it worked immediately. The answer cited my file, and both dense and BM25 ranked the passage first.

Then I ticked the Concept graph and asked the same question.

Instead of an answer, I got a red technical error: "graph retrieval failed: Graph retrieval supports only selected Kestrel source versions."

The trace showed the full story. Dense and BM25 both worked and found the right chunk. The graph step failed. The whole question ended as an error with 0 model calls, so I got no answer at all, even though two of three searches had succeeded.

I also opened the Concept map. My document was not there. The graph only existed as a saved snapshot of the Kestrel demo, and nothing built a graph when I uploaded a file.

This did not match what the professor asked for: a graph that can be built from a new document, explored in the map and used as a retriever.

### What I changed

I decided to work on this. For each decision, I want to write what I chose, why, and what else could have been done.

**A graph for uploaded documents** (`rag_app/doc_graph.py`).  
I chose to use the model to extract concepts and links from each passage. Every concept and link must come with a quote that is copied exactly from the passage, and the entity name must appear in its quote. Anything that does not pass is dropped and counted. Contact details are replaced before a passage is sent.  
I chose this because the professor asked for it, and because strict evidence stops the model from inventing facts. Another approach would have been to build the graph lazily on the first question, but that makes the first answer slow. Another would have been a button only, which is easy to forget. The final application uses a Build graph button. Feras changed the default so that nothing is sent to the model until the user clicks, because building a graph costs model calls.

**A generic schema** instead of the Kestrel types.  
Uploaded documents can be about anything, so a fixed list of entity types would extract almost nothing. The cost is that a free-form graph is messier than a fixed ontology.

**A soft failure.**  
If the graph is missing or fails while other methods are selected, the graph is reported as unavailable and the other methods still answer. This is the opposite of what happened in my T10, where one failing part killed the whole question.

**A fix for mixed selections.**  
While testing, I found that selecting the Kestrel files together with any other file switched the graph off. A question that the graph answers on its own returned "insufficient evidence" as soon as one extra file was ticked. Now the graph runs on the files it covers and lists the others as not covered.

**A guard against rich text saved as `.txt`.**  
TextEdit saves rich text by default, so a file named `.txt` was stored with markup inside the chunks, which polluted retrieval. Now such uploads are refused with advice to save as plain text.

**A configurable model** (`rag_app/llm.py`).  
The application assumed Google. I made `LLM_URL`, `LLM_API_KEY` and `LLM_MODEL` read in one place, used for answers and for graph extraction. Google stays the default and the old names still work. Replacing Google entirely was another option, but it would have broken the original setup.

**A Metrics tab.**  
It shows outcomes, abstention rate, latency, which retrievers were used, model calls and tokens. It is computed from the traces that already exist, so nothing new is stored.

**24 new tests.**  
They cover the graph validation, redaction before extraction, failing models, two-hop retrieval, the fallback, mixed selections, the rich text guard, the model settings and the metrics. The tests clear the model variables so they never call a real model.

### What happened after

After I submitted my branch, Feras merged it and made further improvements: a configurable timeout, a fix so that an unrelated graph cannot push a good passage out of the top five, and a security fix so that a Google key is never sent to another endpoint. I mention this because the final application is the result of both our work, and these later fixes are his.

## 7. The Numbers, and a Mistake I Made

In my first testing report, I wrote that 195 tests passed on the original code, and 198 after my changes.

When Feras checked the published code, he found 174 tests, not 195. He added a note to my report.

He was right. My notes showed 174, and my 24 new tests make 198. I wrote 195 wrongly.

I am including this in my report because it taught me something. A number in a report is a claim, and someone else should be able to reproduce it.

The reproducible numbers are:

- 174 tests on the original code.
- 198 tests on my branch (174 plus my 24 new tests).
- 209 tests after Feras's later fixes.

## 8. Course Ideas I Understood Better Because I Tested

**A prompt is a request. Code is a guarantee.**  
The prompt asks the model to answer only from the evidence. But what really protects the user is the code: an answer must cite a chunk, an abstention must cite nothing, and cited chunks must have really been retrieved. When I saw the application reject outputs that break these rules, I understood this sentence for the first time.

**Verification is not evaluation.**  
Passing tests tell me the code works. They do not tell me the answers are good. For that, we need questions with known right answers and measures like Recall. The tests I wrote could never have shown me that the graph helps two-step questions. My ten manual tests and our retrieval evaluation did.

**Traces make debugging possible.**  
When the graph failed on my file, the trace showed me exactly which step failed and that the model was never called. Without it I would have been guessing.

**Faithfulness is not correctness.**  
An answer can stick perfectly to the passage it was given and still be wrong if the passage is the wrong one. In our application, the references let a human check this. We do not measure faithfulness automatically.

## 9. Limits and What I Would Improve

| Issue | Why it should change | Solution |
| --- | --- | --- |
| Abstaining still costs a model call | The application pays for an answer it already knows will be "no" | Add a minimum relevance score before calling the model |
| Names are not hidden | A name in a document or question reaches the provider | Add name detection and measure its false alarms |
| "Ask a question about this concept" runs a fresh question | One answer left out an error code that the map clearly showed | Start the search from the passages linked to the clicked concept |
| Chunks are fixed 800-character windows | Some chunks start in the middle of a word and cut a table row | Split on sentences or headings, then measure Recall again |
| Graph quality depends on the extraction model | A name like "Project Helios" versus "Helios" can fall back to weaker matching | Merge similar names, and measure the result |
| Search settings reset after a page refresh | Two of my "insufficient evidence" results were caused by this, not by a defect | Remember the choice, and always re-tick all three when demoing |

## 10. What I Learned

At the beginning, I thought testing meant checking that the application does not crash.

Now I think testing an AI application means asking different questions.

Can I check where the answer came from? What happens when the answer is not there? What leaves my computer? What does it cost? What breaks when I use my own data?

I learned that a good AI system is not only one that gives correct answers. It is one that lets you verify them, shows what it did, admits what it cannot do, and fails safely.

I also learned that finding a problem is useful only if I can explain it clearly, and that fixing it creates new responsibilities: tests, documentation and honest numbers.

Finally, I learned something about my own work. Being honest about which parts I wrote, which parts AI helped with and which numbers I got wrong made my report stronger, not weaker.

If I continue, I would like to study how to measure faithfulness automatically, how to compare embedding models, and how to detect personal names reliably.
