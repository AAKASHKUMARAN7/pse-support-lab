# Submission

- **Name:** Aakash M
- **Date submitted:** 14 November 2026
- **Repository link:** https://github.com/AAKASHKUMARAN7/pse-support-lab
- **Total time spent (real time):** about 2.5 hours (14 Nov 2026, ~09:05–11:30 IST); see the time log

> Replies below are drafts written on the **exercise clock** (Monday 16 November 2026, Asia/Dubai). Keep your real time in the time log at the end. Put screenshots, log excerpts and query output in `evidence/` and link to them.

- **Items I fully investigated, and why I chose them:** All five, worked in this order: **2 → 1 → 4 → 3 → 5**.
  - **#2 (API restarts, P1)** first: production-wide, customers getting 502s, invoices not reaching the ASP, a critical alert, and a go-live in two days.
  - **#1 (Oasis)** started before the alert (it arrived first, at month-end) and finished as soon as the P1 was stable, because I'd promised Rashid an answer by 10:30 and it was answerable from the database.
  - **#4 (Sahara)** before #3: both are P2, but Sahara's problem is *silent* (status says "Submitted"), can't be fixed by the customer, and has a payment run behind it.
  - **#3 (Al Noor)**: auditor deadline.
  - **#5 (Ghaf)** last: P3, product working as documented.

  #3 and #5 turned out to be quick once the evidence was in place, so I completed them fully rather than leaving "what I would check next" notes.
- **How to read the evidence:** everything is in [`evidence/`](evidence/) (index in [evidence/README.md](evidence/README.md)). Evidence files carry the **real UTC time of my lab run (14 Nov 2026)**; the replies and logs below use the **exercise clock** (Mon 16 Nov, Asia/Dubai). I reproduced every issue on my own machine with the customers' files and `make load`. `make` isn't installed on my Windows machine, so I ran the Makefile's `docker compose` commands directly.

---

## Incident 1 — `inbox/01-oasis-builders-upload-stuck.md`

### Acknowledgement

- **Sent at (exercise clock):** 09:15 (email received 09:05, P2 first-response target 10:05)
- **Reply:**

> Hi Rashid,
>
> Thank you for writing in, and I understand this is month-end for you, so getting these invoices out today matters.
>
> To make sure I have it right: you uploaded the November file three times this morning. The first two sat on "Processing", the third ended with an error page, and now some invoices say the document number "already exists". You need to know which invoices have actually gone out, and how to send the rest without duplicates.
>
> You did the right thing by stopping. Please don't upload the file again until you hear from me. The portal checks invoice numbers so the same invoice can't be sent twice, and I'll confirm that for your invoices as part of my check.
>
> I'm going through all of this morning's uploads for Oasis Builders now. I'll send you an invoice-by-invoice list of what was sent and what wasn't by 10:30 at the latest, and I'm happy to call you on +971 6 555 0142 once I have it.
>
> Kind regards,
> Aakash M
> Invoicely Lite Support

### Priority and justification

- **Priority:** P2
- **Why:** Invoices are reaching the ASP for other customers and (as it turned out) for Oasis too, so it isn't P1. But it's a major degradation for this customer: their monthly file can't be uploaded normally, they don't know what was issued, and there's a duplicate risk on tax invoices. On top of that, it's **month-end** (the controller can't close the period) and their buyers are waiting. The SLA guide says business impact like month-end makes the same problem more urgent. Once I'd confirmed all 8 invoices were delivered exactly once (10:20), the customer impact was resolved. I raised the underlying product defect to engineering separately as **P3**, because a workaround exists (smaller files, check the batch page before retrying).
- **SLA deadlines I am working to** (first response / next update / resolution target): first response by 10:05 (sent 09:15); next update promised by 10:30 (resolution sent 10:20); resolution target 8 h (17:05). In practice the customer's question was answered within about 75 minutes of the email.

### Investigation log

| Time (exercise clock) | What I checked / did | What I found |
|---|---|---|
| 09:15 | Acknowledged; asked him not to re-upload | — |
| 09:18 | DB: this morning's imports for seller 2 (Oasis) ([evidence](evidence/07-oasis-db-state.txt)) | **3 imports** of `oasis-builders-nov-2026.xlsx`, all **Completed** on the server, each taking **138–157 seconds**. So the uploads didn't fail; the server finished all three. |
| 09:22 | DB: outcome of every invoice number across the 3 uploads | Each of OBS-2611-001…008 is **Accepted exactly once**: 001–003 by upload 1, 004–008 by upload 3. Every other copy is "Rejected — AE-BR-09 already exists". This answers his question 1. |
| 09:25 | Cross-checked on the ASP side: `GET /v1/documents?sender=0235:1003182746` | The ASP holds exactly **one accepted document per invoice number**. No duplicates reached his buyers. |
| 09:30 | Why "already exists" on the *first* upload? Read the AE-BR-09 errors | Upload 1's invoices 004–008 were rejected "already exists with status **'Parsed'**", i.e. against copies that uploads 2 and 3 had *just created* and not yet sent. Hypothesis: a race between parallel uploads of the same file. |
| 09:35 | Code: [importer.go:87](services/api/internal/importer/importer.go#L87) and [store.go:298-301](services/api/internal/store/store.go#L298-L301) | Confirmed. The importer inserts all invoices as `Parsed` *before* validating them, and the duplicate check counts any non-rejected invoice in another import, **including `Parsed`** ones that are still being processed. Two uploads of the same file running at once reject each other's invoices. Which upload "wins" each invoice depends on timing. |
| 09:40 | Why is one upload so slow? Grafana "Import processing time p50/p95" and "Participant lookups"; [validate.go:69](services/api/internal/validate/validate.go#L69) + [validate.go:166](services/api/internal/validate/validate.go#L166) | The Peppol participant lookup runs once **per row**, not once per buyer, with no caching. His file is 600 rows but only **5 distinct buyers**. At ~0.228 s per lookup (693.8 s / 3049 lookups from `/metrics`), that's **~137 s** just for lookups ([evidence](evidence/07-oasis-timing.txt)). It's "a bigger month", so it's the first time the file has crossed the limit below. |
| 09:42 | Alert for Incident 2 fired → switched to P1 | — |
| 10:10 | Back on Oasis: portal proxy logs (`docker compose logs web`) | Three lines `"path":"/imports","status":504,"durationMs":~60000,"error":"TimeoutError"`. The portal gives up after **60 s** ([route.ts:6](web/app/api/%5B...path%5D/route.ts#L6)) and shows *"The upload did not complete in time (504 Gateway Timeout). Please try again."* ([UploadForm.tsx:8](web/components/UploadForm.tsx#L8)). But the API keeps going, because the import runs on `context.Background()` with a 10-minute budget ([importer.go:22,38](services/api/internal/importer/importer.go#L38)). The screen literally tells him to upload again, which is what caused uploads 2 and 3. |
| 10:12 | Dead end: is this Incident 2 (API restarts)? | No. His uploads were before 09:05 and the restarts started ~09:27, and the API logs show the three imports completing normally. They are related, though: big imports hold memory, and an API restart *during* a big import would leave it stuck in Processing (see Incident 2). |
| 10:15 | Reproduced: uploaded his file 3 times through the **portal** (port 3000), one after another, as he did ([evidence](evidence/07-oasis-portal-uploads.txt)) | Uploads 1–3: **HTTP 504 after ~60 s** each; server finished them 138–157 s later; final result as above (all 8 delivered once, the rest AE-BR-09). The replay (`make load`) shows the same: Oasis HTTP 201 only after **135 s** when called directly without the proxy. |
| 10:20 | Sent resolution reply; offered a call | — |
| 15:00 | Raised a bug with engineering (P3) | Note below. |

### Root cause

- **What happened:** His November file (600 lines) takes about 2½ minutes to process, because the portal checks the buyer's Peppol registration once per line. The portal page only waits 60 seconds, then shows a timeout error that says "Please try again", while the upload carries on and completes in the background. He tried again twice. The three copies were processed at the same time, and the duplicate check stopped each copy from issuing invoices another copy had already started. The result: every invoice was sent exactly once, but spread across uploads 1 and 3, with "already exists" on the other copies. Hence the confusion.
- **Where** (component, `file:line`):
  - Slowness: api, [validate.go:166](services/api/internal/validate/validate.go#L166) (participant lookup per row inside the row loop, [validate.go:69](services/api/internal/validate/validate.go#L69)); 200 ms SMP latency simulated at [asp-mock main.go:40](services/asp-mock/main.go#L40).
  - Timeout + "try again": web, [route.ts:6](web/app/api/%5B...path%5D/route.ts#L6) (`UPSTREAM_TIMEOUT_MS = 60_000`) and [UploadForm.tsx:8](web/components/UploadForm.tsx#L8); the import is synchronous inside `POST /v1/imports` ([importer.go:37-126](services/api/internal/importer/importer.go#L37-L126)) and isn't cancelled when the browser gives up ([importer.go:38](services/api/internal/importer/importer.go#L38)).
  - "Already exists" race: [importer.go:87](services/api/internal/importer/importer.go#L87) (insert as Parsed before validating) + [store.go:301](services/api/internal/store/store.go#L301) (duplicate check counts `Parsed` invoices of other in-flight imports).
- **Why it happens:** Upload time grows with the number of lines (about 0.23 s per line), and the portal's patience is fixed at 60 s. Any file above roughly 250 lines times out in the browser while succeeding on the server, and the UI then invites a duplicate upload.
- **Evidence:**
  - Server-side import timings: `"msg":"import completed" … "rows":600,"invoices":8,"validated":3,"rejected":5,"duration_ms":156813` (upload 1), 147842 (upload 2), 138031 (upload 3) — [evidence/07-oasis-timing.txt](evidence/07-oasis-timing.txt)
  - Portal proxy: `"status":504,"durationMs":60637,"error":"TimeoutError: The operation was aborted due to timeout"` ×3 — same file
  - DB, per-invoice outcome matrix and the ASP cross-check — [evidence/07-oasis-db-state.txt](evidence/07-oasis-db-state.txt)
  - Metrics: `invoicely_participant_lookup_duration_seconds_sum 693.76 / _count 3049` → 0.228 s per lookup; import duration histogram has 4 imports above 120 s (all Oasis)
  - Grafana "Import processing time p50/p95" — [g6-import-processing-time.png](evidence/screenshots/g6-import-processing-time.png) (p95 far above 60 s; exact times are in the logs because the histogram jumps from a 120 s to a 300 s bucket)
  - Portal batch page for upload #1: processing time **156.8 s**, Accepted 3 / Rejected 5 — [p1-oasis-batches.png](evidence/screenshots/p1-oasis-batches.png)
- **Confidence and open questions:** High on both mechanisms (reproduced end to end). Open: (1) he says the first two attempts "sat on Processing" for "a good few minutes". In my reproduction the error appears at 60 s, so he may have left the tab before the error showed, or the morning's load made it slower. Worth asking him, but it doesn't change the fix. (2) The exact split of which upload sent which invoice in production depends on his real timing. The reply uses the production data, not my lab run. (3) If a timed-out import is ever killed mid-way (Incident 2), its invoices stay `Parsed` and would block those numbers forever. I've asked engineering to check for that.

### Customer resolution reply OR escalation note

- **Which one and why:** **Resolution reply to the customer** (his questions are fully answerable from our data, and nothing needs repairing), plus a **P3 bug report to engineering** (not an urgent escalation), because the slow-upload + timeout + race will hit him again next month and will hit any customer with large files.

#### Resolution reply (sent 10:20)

> Hi Rashid,
>
> I've finished checking, and the short answer is good news: **all 8 of your November invoices have been issued, each exactly once.** Nothing has been sent twice, and nothing is missing.
>
> **1. Which invoices have been sent**
>
> | Invoice | Buyer | Total (AED) | Status | ASP reference (start) |
> |---|---|---|---|---|
> | OBS-2611-001 | Crescent Contracting LLC | 469,807.80 | Accepted | dcea9667… |
> | OBS-2611-002 | Northstar Engineering Consultants LLC | 506,761.50 | Accepted | 51023d19… |
> | OBS-2611-003 | Coral Reef Resorts LLC | 383,475.75 | Accepted | 2a144e97… |
> | OBS-2611-004 | Bluewater Facilities Management LLC | 466,130.70 | Accepted | b9f62e19… |
> | OBS-2611-005 | Crescent Contracting LLC | 586,164.60 | Accepted | 0a8aa41d… |
> | OBS-2611-006 | Gulf Horizon Transport LLC | 427,919.10 | Accepted | 99fce943… |
> | OBS-2611-007 | Northstar Engineering Consultants LLC | 356,633.55 | Accepted | 75cc3085… |
> | OBS-2611-008 | Coral Reef Resorts LLC | 615,742.05 | Accepted | 9c2a2af0… |
>
> "Accepted" with an ASP reference means our network provider has taken the invoice and it's on its way to your customer. I also checked on the provider's side: they hold exactly one copy of each.
>
> **What happened:** your uploads didn't fail. Because this month's file is bigger, the portal took about two and a half minutes to process it, but the upload page only waits one minute before showing an error. So while the screen told you something had gone wrong, the upload was still being processed in the background. When you uploaded again, the portal correctly refused to issue the same invoice numbers a second time. Those refused copies are the "already exists" messages you saw. They weren't sent anywhere, and you can ignore them. Because three copies were being processed at the same time, invoices 001–003 went out from your first upload and 004–008 from your third. That's why the batch pages looked so confusing.
>
> I'm sorry about this. The page showing an error and asking you to try again, when the upload was actually working, is a fault on our side.
>
> **2. What to do now**
>
> Nothing more for November. Please don't upload the file again; everything is out.
>
> **For next month, until we've fixed this:**
>
> - If the upload page shows an error, open **Batches** in the portal before trying again. Your upload will usually be there and still working.
> - Or split the file into smaller files of about **150 lines each** (two invoices per file). Each one then finishes well within the time limit.
>
> I've reported the slow processing and the misleading error to our engineering team, and I'll let you know when it's fixed so you can go back to a single monthly file.
>
> If it would help your controller to close the period, I'm happy to send this list as a spreadsheet, or to call you on +971 6 555 0142. Just reply with a good time.
>
> Kind regards,
> Aakash M
> Invoicely Lite Support

#### Bug report to engineering (sent 15:00, P3)

```markdown
### Escalation: Large uploads time out in the portal at 60 s but finish server-side; UI says "try again"; parallel copies race on AE-BR-09

**Priority:** P3 — no data loss and customer resolved (all 8 invoices delivered once); workaround exists (split file, check Batches). Will recur for every month-end file > ~250 lines.
**Customer / seller:** Oasis Builders Supply LLC, seller id 2 (first reporter); affects any seller with large files
**Reported by / at:** Rashid Al Mansoori, email, 09:05 Mon 16 Nov
**Affected:** 3 imports of oasis-builders-nov-2026.xlsx (lab ids 5ec45bb9…, 71dbc094…, 94f1c2dd…), 8 invoices OBS-2611-001..008 — all Accepted once; 16 AE-BR-09 rejections on the extra copies

**Symptoms (customer view):**
Upload page spins ~60 s then shows "504 Gateway Timeout. Please try again." Re-uploads show "Document number already exists" — including on invoices of the FIRST upload.

**Evidence:**
- web log: {"msg":"proxy","level":"error","method":"POST","path":"/imports","status":504,"durationMs":60637,"error":"TimeoutError: …"} ×3
- api log: "import completed" rows=600 invoices=8 duration_ms=156813 / 147842 / 138031
- metrics: invoicely_participant_lookup_duration_seconds sum/count = 693.76/3049 → 0.228 s per lookup; 600 lookups per Oasis file (5 distinct buyers)
- DB: upload 1 invoices 004–008 rejected "AE-BR-09 … with status 'Parsed'" (copies from uploads 2/3 still in flight)

**Steps to reproduce:**
1. In the portal (http://localhost:3000), upload samples/oasis-builders-nov-2026.xlsx as Oasis Builders.
2. At the 504 (60 s), upload again; repeat once more.
3. ~3 min later: all three imports Completed; each invoice Accepted once, spread over uploads 1 and 3.

**What I have already tried / ruled out:**
- Not the API restarts of Incident 2 (imports completed normally, no restart in that window).
- Not a customer data problem (no other validation errors; same file passes when uploaded once and left alone).

**Suspected cause (with confidence):** High.
1. validate.go:166 — participant lookup per row (no per-import cache) → O(rows) × 200 ms.
2. web/app/api/[...path]/route.ts:6 — 60 s proxy timeout on a synchronous import (importer.go:37-126 runs inside the request; importer.go:38 uses context.Background(), so it is not cancelled).
3. UploadForm.tsx:8 — 504 message tells the user to "try again".
4. importer.go:87 + store.go:301 — duplicate check counts other imports' invoices in status Parsed, so in-flight copies reject each other.

**Workaround in place:** Yes — customer told to check Batches before retrying, or split into ~150-line files.

**Timeline:**
- 09:05 email · 09:15 ack · 09:18–09:40 DB + code analysis · 10:15 reproduced via portal · 10:20 customer resolved · 15:00 this report

**Ask:** (1) Cache participant lookups per import (5 lookups instead of 600) — biggest, simplest win. (2) Make imports asynchronous (return 202 + import id, show progress) or at least raise the proxy timeout above the import budget, and change the 504 message to "Your file is still processing — check Batches before uploading again". (3) Don't count `Parsed` invoices of other imports in AE-BR-09, or reject a second upload of the same file while the first is in flight. Rough ETA for (1) by end of week so I can tell the customer before their December run?
**Next customer update due:** when fix is scheduled; latest Fri 20 Nov
```

### Workaround offered

- Nothing to redo for November (all 8 delivered once).
- Until fixed: after an error on upload, check **Batches** before uploading again; or split the monthly file into ~150-line files (2 invoices each). At ~0.23 s per line that's about 35 s, under the 60 s limit even on a busy morning.

### Prevention ideas

- **Cache the participant lookup per import / per buyer** (5 calls instead of 600): about 137 s down to about 1 s for this file. Cheapest fix with the biggest effect.
- **Make imports asynchronous:** return immediately with the import id and show progress on the batch page, instead of holding the browser request open.
- **Never tell the user to "try again" on a timeout** when the server may still be working. Say "still processing — check Batches", and/or block a second upload of the same file while one is in flight (e.g. by file hash).
- **Fix the duplicate check** so it ignores (or waits for) invoices still being processed by another import.
- **Monitoring:** alert on import duration p95 > 45 s (we're close to the 60 s cliff before customers notice) and on web 504s on `/imports`.
- **Support knowledge base:** "Upload shows 504: check the Batches page first, and run the per-invoice query before advising a re-upload."

---

## Incident 2 — `inbox/02-alert-api-restarted-marina-bay.md`

### Acknowledgement

- **Sent at (exercise clock):** 09:45 short note in the on-call channel that I've picked up the alert; 09:55 reply to Priya (alert fired 09:42, P1 first-response target 10:12 at the latest)
- **Sent to:** Priya Nair (Customer Success), copied to `support-oncall` and posted in #cs-escalations where she raised it
- **Reply:**

> Hi Priya,
>
> Yes, I'm owning this. Thanks for forwarding it.
>
> What I can see so far: the API restarted 3 times between roughly 09:27 and 09:42. While it's restarting the portal can't reach it, which is very likely where your customers' "502 Bad Gateway" errors come from. I'm treating the invoices sitting in "Validated" since about 09:30 as part of the same incident until I can prove otherwise.
>
> I've raised it as P1 and I'm paging engineering on-call as soon as I've confirmed which customers are affected, in the next few minutes. My next update to you is at 10:30, then every 30–60 minutes until it's stable.
>
> On Marina Bay's go-live on Wednesday: I can't honestly give you a yes or no yet. You'll have a clear view from me, with what has to be true for Wednesday to be safe, before your afternoon call. If you can tell me the time of that call, I'll make sure you have it an hour before.
>
> For customers asking you right now: please ask them not to keep re-uploading the same file if they get a 502. I'll check whether their invoices went through and tell them, so we don't end up with confusing duplicates.
>
> Thanks,
> Aakash M

### Priority and justification

- **Priority:** P1
- **Why:** The SLA matrix's first question is "Can customers get invoices to the ASP at all?" While the API is restarting, **no** customer can (every portal request returns 502), and invoices that were waiting to be sent at the moment of a restart are left in "Validated" and **never reach the ASP** until someone intervenes. That's what Priya's customers describe ("sitting in Validated since about 9:30"). Several customers are affected, it's production, and the alert is `severity=critical`. Business impact: **Marina Bay goes live on Wednesday** and their GM is already nervous. The escalation policy says to page engineering on-call for a P1 as soon as the impact is confirmed, without waiting for a full root cause, which is what I did at 10:00.
- **SLA deadlines I am working to:** first response 15–30 min from the alert (09:42) → by 10:12 (on-call channel 09:45, Priya 09:55); updates every 30–60 min (10:30, 11:30, 12:30, 14:00); resolution target 4 h → 13:42, which I read as "stable, with a workaround in place and the stranded invoices recovered". The permanent memory fix is engineering's change; I track it but don't promise a date I don't control.

### Investigation log

> Times below are on the exercise clock. The lab evidence files carry the real UTC times of my reproduction on 14 Nov (the first real out-of-memory kill was at 04:43:52Z, roughly "09:27" in the story).

| Time (exercise clock) | What I checked / did | What I found |
|---|---|---|
| 09:42 | Alert received. Opened Grafana "Invoicely Lite – Overview" ([g1](evidence/screenshots/g1-overview-row.png), [g2](evidence/screenshots/g2-container-memory.png), [g4](evidence/screenshots/g4-container-restarts.png)) | "API up" flaps 1 → 0 → 1; "API process restarts (1h)" > 0; "Container memory (working set)": the **api** line climbs steadily to the **128 MiB limit, then drops to ~8 MiB** at each restart (sawtooth). Nothing else restarts. |
| 09:45 | Posted in the on-call channel that I'd picked it up | — |
| 09:47 | `docker events` / `docker inspect` on the api container ([events](evidence/08-api-docker-events-readable.txt)) | `oom` → `die exitCode=137` → `start`, **twice** in my reproduction (04:43:59Z and 04:50:39Z). Exit 137 = killed by the kernel for exceeding its memory limit. `MemoryLimit=134217728` (128 MiB) and `MemorySwap` equal to it, i.e. no swap ([docker-compose.yml:60-61](docker-compose.yml#L60-L61)). `RestartCount=2`. |
| 09:48 | API log around the kill ([logs](evidence/08-incident2-logs.txt)) | The last line before each kill is in the middle of normal work (`asp response …`, `import parsed … drt-morning-61.xlsx`), with **no shutdown message**, then `api starting` ~50 s later. That's a hard kill, not a crash in our code (no panic or stack trace). |
| 09:50 | Priya's message arrives (502s, invoices stuck in Validated) | — |
| 09:51 | Portal side: probed the portal once a second ([probe](evidence/08-portal-probe.log)) | `GET /api/imports → 502` for ~25 s during the second restart (04:50:33–04:50:58Z), back to 200 after. Exactly the "502 Bad Gateway on and off" her customers report: the web proxy can't reach the API ([route.ts:43](web/app/api/%5B...path%5D/route.ts#L43)). |
| 09:53 | DB: what did the restarts leave behind? ([after restart](evidence/08-incident2-db-after-restart-1.txt), [scope](evidence/09-scope-queries.txt)) | **3 imports stuck in "Processing" forever** (Zayed Port, Desert Rose and **Marina Bay** `mbh-morning-158.xlsx`). **12 invoices stuck in Parsed, 11 stuck in Validated**, all last changed at the moment of a kill. Several customers affected, so the P1 is confirmed. |
| 09:55 | Replied to Priya | — |
| 10:00 | **Paged engineering on-call** with the escalation note below (impact confirmed; suspected cause added at 10:20) | — |
| 10:05 | Why does memory keep growing? Grafana "API Go heap in use" + Prometheus export ([table](evidence/11-prometheus-api-memory-restarts.txt)) | Heap in use goes 7.9 → 13 → 19 → 33 → 52 → 64 → 104 MiB over ~18 minutes of uploads and **never comes back down between uploads**, even when idle. That's a leak/retention pattern, not a spike. Each big Oasis upload adds several MiB at once. |
| 10:10 | Code: what does the API keep per upload? [sources.go](services/api/internal/importer/sources.go) + [importer.go:95](services/api/internal/importer/importer.go#L95) | **Root cause.** Every import puts the raw file bytes, the whole parsed Excel workbook (`*excelize.File`), all rows and all mapped invoices into `SourceCache`, an in-memory map that is **never emptied**. There's no delete or eviction, and `StoredAt` is set ([sources.go:32](services/api/internal/importer/sources.go#L32)) but never read. It exists to show the source rows and offer the original download on the batch page. With a 128 MiB limit, every busy morning ends in an OOM kill. |
| 10:15 | Why are invoices stuck in Validated? [submit.go:65](services/api/internal/submit/submit.go#L65), [importer.go:125](services/api/internal/importer/importer.go#L125), [main.go:56-57](services/api/main.go#L56-L57) | The submission queue is an **in-memory Go channel**. Validated invoices are only queued at the end of an import. When the process is killed, the queue is lost, and on startup nothing re-reads Validated invoices from the database. They wait until someone presses **Retry**. |
| 10:18 | Why are imports stuck in Processing / invoices in Parsed? [importer.go:87](services/api/internal/importer/importer.go#L87), [importer.go:117](services/api/internal/importer/importer.go#L117) | The import runs inside the upload request. Invoices are inserted as Parsed first, then validated one by one. If the process dies half-way, `FinishImport` is never reached: the import stays "Processing" and its remaining invoices stay "Parsed" for good. |
| 10:20 | Updated the escalation with the suspected cause | — |
| 10:25 | **Workaround:** "Retry stuck invoices" (`POST /v1/imports/{id}/retry`) on every import with Validated/Failed invoices ([evidence](evidence/10-incident2-workaround.txt)) | `requeued 5 / 4 / 2 / 2` → 12 s later **all 13 Accepted** (Desert Rose, Zayed Port, Marina Bay). Safe: retry only acts on Validated/Failed ([submit.go:111](services/api/internal/submit/submit.go#L111)), so it can't double-send. |
| 10:30 | Update to Priya | — |
| 10:35 | Can the **Parsed** ones be recovered by support? | **No.** `POST /v1/invoices/{id}/retry` → **409** "current status: Parsed" ([httpapi.go:270](services/api/internal/httpapi/httpapi.go#L270)). Worse, re-uploading the same invoice gives **AE-BR-09 "already exists … with status 'Parsed'"** ([store.go:301](services/api/internal/store/store.go#L301)). So the number is **blocked for good**: never sent, not retryable, not re-uploadable. Added a data-repair ask to the escalation. |
| 10:45 | Dead end 1: is the ASP or the database failing? | No. Only the api container has `oom/die/start` events; asp-mock and postgres were up throughout; `/healthz` (which pings the DB) answers 200 between restarts. |
| 10:50 | Dead end 2: is one "bad" Marina Bay file crashing the API? | No. The first kill happened during a Desert Rose upload and the second during a Marina Bay one. It's whichever upload tips memory over the limit. Marina Bay's other **46 imports / 276 invoices** this morning were all Accepted ([scope](evidence/09-scope-queries.txt) §3). |
| 11:00 | Dead end 3: does the alert count match reality? Grafana alert state ([evidence](evidence/12-grafana-alert-state.txt)) + raw `process_start_time_seconds` | **The alert over-counts.** In my lab it went "firing" at 04:27:40Z, 16 min **before** the first real kill. The API's `process_start_time_seconds` drifts by exactly −1 s at a time while the same process is running (…271.4 → 270.4 → 269.4), most likely the container VM's boot-time clock drifting under load. `changes()` counts every wobble as a restart. The real restarts are the large forward jumps (+1186 s at 04:45, +395 s at 04:51). So the "restarts=3" in the alert should be cross-checked against `docker events` / RestartCount. |
| 11:05 | Dead end 4: why did "Invoicely API 5xx responses" not fire? | It counts 5xx **returned by the API**. When the API is dead, the 502s are produced by the **web proxy** and never reach that metric, so the 5xx alert is blind exactly when it matters. |
| 11:30 | Update to Priya | — |
| 13:30 | Scope and go-live assessment for Marina Bay ([scope](evidence/09-scope-queries.txt)) | See the 14:00 update below. |

Also observed (excluded from the root cause): while my laptop (6 GB RAM in total) was swapping after the second kill, the API logged `participant lookup failed … context deadline` and `asp request failed`, and Docker itself stopped answering for a few minutes. That was my machine, not the product. I stopped the replay at 175/240 peak uploads, once the evidence was captured. It did show one more weakness: when the participant lookup fails, the validator only logs a warning and **lets the invoice through without the AE-BR-11 check** ([validate.go:168-169](services/api/internal/validate/validate.go#L168-L169)).

### Root cause

- **What happened:** The API keeps a full copy of every uploaded file, plus its parsed workbook, in memory, and never frees it. Over a busy morning that grows until the container hits its 128 MiB limit, and the kernel kills the process (exit 137). Docker restarts it after ~30–50 s. While it's down, every portal request returns 502. Invoices that were queued to be sent at that moment are forgotten (the queue lived only in memory), so they sit in "Validated". Uploads that were half-way through stay "Processing" for good, with their invoices stuck in "Parsed".
- **Where** (component, `file:line`):
  - Unbounded cache: api, [services/api/internal/importer/sources.go:22-43](services/api/internal/importer/sources.go#L22-L43) (map with no eviction), filled at [importer.go:95](services/api/internal/importer/importer.go#L95) for every import.
  - Memory limit, no swap: [docker-compose.yml:60-61](docker-compose.yml#L60-L61).
  - Lost queue: [submit.go:65](services/api/internal/submit/submit.go#L65) (in-memory channel), [importer.go:125](services/api/internal/importer/importer.go#L125) (queued only at the end of an import), [main.go:56-57](services/api/main.go#L56-L57) (no re-queue on startup).
  - Stuck Processing/Parsed: [importer.go:87](services/api/internal/importer/importer.go#L87) and [importer.go:117](services/api/internal/importer/importer.go#L117); not retryable at [httpapi.go:270](services/api/internal/httpapi/httpapi.go#L270); blocks the number at [store.go:301](services/api/internal/store/store.go#L301).
- **Why it happens:** The cache was presumably added so the batch page can show source rows and offer the original file for download. Nothing ever removes entries, and the parsed `excelize.File` is far bigger than the file itself. Memory is a function of "uploads since last restart", so the problem appears on the busiest mornings and goes away by itself after each restart, which also explains the "on and off" pattern.
- **Evidence:**
  - Docker: `04:43:52Z oom` · `04:43:59Z die exitCode=137` · `04:44:31Z start` · `04:50:29Z oom` · `04:50:39Z die exitCode=137` · `04:50:52Z start`; `RestartCount=2 MemoryLimit=134217728 MemorySwap=134217728` — [evidence/08-api-docker-events-readable.txt](evidence/08-api-docker-events-readable.txt)
  - Prometheus: api working set 7.9 → 111 MiB, then 7.9 after restart; 22 → 128 MiB, then 31 after the second; heap in use tracks it — [evidence/11-prometheus-api-memory-restarts.txt](evidence/11-prometheus-api-memory-restarts.txt) (query: `container_memory_working_set_bytes{container_label_com_docker_compose_service="api"}`, `go_memstats_heap_inuse_bytes{job="api"}`)
  - Logs: no shutdown line before `api starting` — [evidence/08-incident2-logs.txt](evidence/08-incident2-logs.txt); Loki: `{service="api"} |= "api starting"`
  - Portal: `502` from 04:50:33 to 04:50:58Z — [evidence/08-portal-probe.log](evidence/08-portal-probe.log)
  - DB: 3 imports stuck Processing, 12 Parsed, 11 Validated — [evidence/09-scope-queries.txt](evidence/09-scope-queries.txt)
  - Workaround and its limits (13 recovered; Parsed → 409 and AE-BR-09 'Parsed') — [evidence/10-incident2-workaround.txt](evidence/10-incident2-workaround.txt)
  - Alert behaviour — [evidence/12-grafana-alert-state.txt](evidence/12-grafana-alert-state.txt)
  - Grafana: [g2-container-memory.png](evidence/screenshots/g2-container-memory.png) (api memory sawtooth), [g3-api-heap.png](evidence/screenshots/g3-api-heap.png) (heap only ever grows until the kill), [g4-container-restarts.png](evidence/screenshots/g4-container-restarts.png) (only api restarts), [g1-overview-row.png](evidence/screenshots/g1-overview-row.png) ("API process restarts (1h)" shows **11** while Docker counted **2**, and "5xx responses" shows **0** during the 502s)
  - Side effect visible in the portal: the Ghaf batch page says *"Source preview is no longer available for this upload"*, because the in-memory file copy was wiped by the restart — [p4-ghaf-batch.png](evidence/screenshots/p4-ghaf-batch.png)
- **Confidence and open questions:** High that the restarts are OOM kills caused by the unbounded cache (memory pattern, exit code 137, and code all agree; nothing else in the API holds memory across requests). Not proven: I didn't rebuild with eviction to show memory going flat. That's engineering's verification. Open: (1) the exact production count of stranded invoices needs the same queries run in production; (2) whether 128 MiB was chosen deliberately (raising it is a quick stopgap but only delays the next kill).

### Customer resolution reply OR escalation note

- **Which one and why:** **Escalation to L3 (P1 page)**, plus updates to Priya (CSM) and through her to the affected customers. It's an infrastructure/code defect, and part of the clean-up (the Parsed invoices and Processing imports) is a data repair support can't do. I keep owning the conversation with Priya and the customers.

#### Escalation note (paged 10:00, updated 10:20 and 10:40)

```markdown
### Escalation: API OOM-killed repeatedly (128 MiB limit) — 502s in portal, invoices stranded in Validated/Parsed

**Priority:** P1 — production; API restarting at peak; while down no customer can upload (502), and invoices queued at the moment of each kill never reach the ASP without manual retry. Several customers affected incl. Marina Bay Hospitality (go-live Wed 18 Nov).
**Customer / seller:** multiple — Marina Bay Hospitality (3), Desert Rose Trading (1), Zayed Port Logistics (8) confirmed; others possible
**Reported by / at:** Grafana alert InvoicelyApiRestarted 09:42; Priya Nair (CSM) 09:50 via #cs-escalations
**Affected:** (lab numbers) 3 imports stuck in Processing: 6c47ab0e… zpl-morning-60, f25dc3ca… drt-morning-61, d49ca28a… mbh-morning-158; 12 invoices stuck Parsed; 11 Validated + 2 Failed (now recovered by retry). Since the first kill (~09:27).

**Symptoms (customer view):**
"502 Bad Gateway" on and off, mostly on upload; invoices sitting in "Validated"; some batches stuck on "Processing".

**Evidence:**
- docker events: oom → die exitCode=137 → start at 04:43:59Z and 04:50:39Z (lab); RestartCount=2; Memory=MemorySwap=128 MiB
- Prometheus: container_memory_working_set_bytes{service=api} 7.9 → 111 → (kill) 7.9 → 128 → (kill) 31 MiB; go_memstats_heap_inuse_bytes rises monotonically between kills
- api log: last lines before each kill are normal work, no shutdown/panic, then "api starting"
- web: GET /api/* → 502 for ~25 s per restart
- DB: SELECT status, count(*) FROM invoices WHERE status IN ('Parsed','Validated') AND updated_at < now()-'5 min' → Parsed 12, Validated 11; SELECT … FROM imports WHERE status='Processing' → 3 rows
- Retry: POST /v1/imports/{id}/retry recovered 13 (Validated/Failed → Accepted); Parsed → 409, and re-upload → AE-BR-09 "already exists … status 'Parsed'"

**Steps to reproduce:**
1. make up; make load (customer replays + 240 peak uploads)
2. Watch Grafana "Container memory (working set)" for api climb to 128 MiB; `docker events --filter container=invoicely-lite-api-1` shows oom/die 137 within ~15 min.

**What I have already tried / ruled out:**
- Not ASP or DB: no restarts there; /healthz OK between kills.
- Not one bad file: kills land on whichever upload tips the limit (Desert Rose, then Marina Bay); Marina Bay's other 46 imports fine.
- Workaround applied: retried all imports with Validated/Failed invoices → 13 Accepted.
- Note: the restart alert over-counts (process_start_time_seconds drifts by −1 s; alert fired 16 min before the first real kill in the lab) — use docker events/RestartCount for the true count.

**Suspected cause (with confidence):** High.
- services/api/internal/importer/sources.go — SourceCache map is never evicted; importer.go:95 stores raw bytes + full excelize.File + rows + invoices for every import → heap grows with uploads until OOM at 128 MiB (docker-compose.yml:60-61).
- Secondary: in-memory submit queue (submit.go:65) is lost on kill and not rebuilt on startup (main.go:56-57) → Validated stranded; imports killed mid-way never reach FinishImport (importer.go:117) → Processing/Parsed forever.

**Workaround in place:** Partial — manual Retry for Validated/Failed (done, 13 recovered). None for Parsed.

**Timeline:**
- ~09:27 — first restart (alert window)
- 09:42 — alert fired · 09:45 picked up · 09:47–09:53 impact confirmed
- 09:55 — CSM informed · 10:00 — on-call paged · 10:20 — cause added · 10:25 — retries done (13 recovered) · 10:40 — Parsed/Processing data-repair ask added

**Ask:**
1. NOW — stop the bleeding: stopgap mem_limit increase for api (e.g. 512 MiB) and/or a cap on SourceCache (evict by age/size; drop the parsed excelize.File after the import completes). Please confirm by 11:00 what you'll deploy.
2. TODAY — data repair: the 3 imports stuck in Processing and their 12 Parsed invoices: either re-validate and queue them, or mark them Rejected ("interrupted by system restart") so customers can re-upload the same numbers. Confirm the list per seller with me before running it; I'll tell each customer.
3. BEFORE WED (Marina Bay go-live) — re-queue Validated (and Failed) invoices on startup; make imports resumable or atomic; and a yes/no from you by Tue 16:00 on whether (1) is the real fix or just a stopgap.
4. Monitoring: fix the restart alert expression (e.g. max_over_time - min_over_time of process_start_time_seconds > 60, or cAdvisor container_start_time_seconds), and alert on web 502s.
**Next customer update due:** Priya 11:30; affected customers via Priya by 12:00
```

#### Update to Priya (CSM) before her Marina Bay call (sent 14:00)

> Hi Priya,
>
> Here's where things stand for your call. Everything below is something I've checked myself.
>
> **What happened this morning:** the API ran out of memory during the busy upload period and restarted. While it restarted (about 30–50 seconds each time), the portal showed "502 Bad Gateway". Invoices that were waiting to be sent at that exact moment were left in "Validated". The cause is on our side: the API was keeping a copy of every uploaded file in memory and never freeing it. It isn't caused by any customer's file, and it isn't specific to Marina Bay.
>
> **What we've done:**
> - Every invoice that was stuck in "Validated" has been re-sent and is now Accepted (13 in total across three customers, including 2 of Marina Bay's).
> - A small number of invoices (4 of Marina Bay's) were caught mid-upload and need engineering to release them. That's scheduled for this afternoon, and I'll confirm to you and to Marina Bay once they're through. Marina Bay doesn't need to re-upload anything; please ask them not to.
> - Engineering has the full details as a P1 and is working on the memory fix.
>
> **For Marina Bay's go-live on Wednesday:**
> - The good news: apart from that one interrupted batch, **all 276 of Marina Bay's invoices this morning (46 uploads) went through and were accepted**. Their data and their setup are fine.
> - The risk is the restarts, which can affect any customer at peak times until the fix is live.
> - What needs to be true for Wednesday: (1) engineering's memory fix deployed, (2) a change so invoices waiting to be sent are picked up again automatically after a restart, and (3) the 4 stuck invoices released. I've asked engineering for a firm yes/no on (1) and (2) by **Tuesday 16:00**.
> - My suggestion for your call: say we found and are fixing a capacity issue that affected all customers this morning, that their invoices were all delivered or are being released today, and that we'll confirm go-live readiness by Tuesday afternoon. If it helps, I'm happy to join the call, and on Wednesday morning I'll personally watch Marina Bay's first batches.
> - One more thing to check with them: if their system will send large batches (more than 8 invoices in one go), tell me. There's a separate issue with large batches (today's Sahara case) that we'd want fixed or worked around first.
>
> Next update from me: 16:00 today, or sooner if engineering confirms the fix.
>
> Thanks,
> Aakash M

### Workaround offered

- **Done by support:** "Retry stuck invoices" on every affected import, which recovered all invoices stuck in Validated/Failed (13 in the lab). Safe to repeat, because it only touches Validated/Failed.
- **Advice to customers (via Priya):** if you get a 502, wait a minute and check the Batches page before uploading again. Don't re-upload a file whose batch is "Processing"; tell support instead.
- **Not possible at L1:** invoices stuck in Parsed inside an interrupted import. These need the L3 data repair.

### Prevention ideas

- **Bound or remove the in-memory file cache.** Evict by age or size, drop the parsed workbook as soon as the import completes, and store the original file in the database or object storage for the download link.
- **Make the submission queue durable.** On startup, re-queue every Validated (and retryable Failed) invoice from the database, or use a DB-backed job table instead of a Go channel.
- **Make imports resumable or atomic.** Either finish an interrupted import on restart or roll it back, so no import is left "Processing" forever and no number is blocked by a "Parsed" ghost.
- **Better alerts:**
  - fix the restart expression so clock drift doesn't fire it (`max_over_time(...) - min_over_time(...) > 60`, or cAdvisor `container_start_time_seconds`)
  - alert when api memory is above 80% of its limit (before the kill, not after)
  - alert on 502/504 from the **web** proxy, which today's 5xx alert can't see
  - alert on "invoices in Validated or Parsed for more than 15 minutes"
- **Capacity test before go-lives:** run `make load` at expected peak plus a margin (it reproduced this in under 20 minutes) as a release gate.
- **Fail closed on lookup errors.** Don't skip AE-BR-11 when the participant lookup fails ([validate.go:168-169](services/api/internal/validate/validate.go#L168-L169)); retry it or mark the invoice for re-check.

---

## Incident 3 — `inbox/03-al-noor-fuel-br-co-15.md`

### Acknowledgement

- **Sent at (exercise clock):** 10:40 (email received 10:15, P2 first-response target 11:15; at 10:30 I was sending the promised P1 update to Priya first)
- **Reply:**

> Dear Fatima,
>
> Thank you for the clear write-up and for attaching the file you uploaded.
>
> To confirm I've understood: several of your November fuel invoices were rejected with BR-CO-15, a check that the invoice total including VAT equals the total before VAT plus the VAT. Other invoices from the same file, prepared the same way, were accepted. You'd like to know why only these failed, what (if anything) you need to change, and how they can be issued correctly, in writing for your auditor.
>
> I'm reviewing the rejected invoices against your file now. For the moment please don't change the figures in your file. Your dispatch records may well be right, and I don't want you to adjust correct numbers to get around a check before we know the cause. Rejected invoices are not issued and don't use up their invoice numbers, so nothing is lost by waiting.
>
> I'll come back to you with what I've found by 13:00 today, and I'll write it so it can go to your auditor as it is.
>
> Kind regards,
> Aakash M
> Invoicely Lite Support

### Priority and justification

- **Priority:** P2
- **Why:** The SLA matrix defines P2 as "subset of invoices rejected": 3 of her 6 invoices were rejected by the ASP, and the other 3 went through. Invoices are reaching the ASP, so it isn't P1. Business impact pushes it towards the top of P2: an **external auditor** is reviewing her November VAT position and wants a written explanation, and it's a compliance rejection on tax invoices. Once I found it was **our calculation** (not her data), I kept P2 but escalated it as a product defect, because any seller with 3-decimal unit prices (fuel, anything sold per litre or kg) can hit it.
- **SLA deadlines I am working to:** first response by 11:15 (sent 10:40); update every 2–4 h (I promised 13:00, sent 12:50; next 16:30); resolution target 8 h, i.e. by 18:15 today. That depends on engineering's fix, so I committed to updates, not to a fix time.

### Investigation log

| Time (exercise clock) | What I checked / did | What I found |
|---|---|---|
| 10:40 | Read the email and the rule text | BR-CO-15 is an **ASP** rule (template field guide → ASP rules): total with VAT (IBT-112) must equal total without VAT (IBT-109) + VAT (IBT-110). The field guide says totals are **not in the file**; the portal calculates them. So her file can't directly contain "wrong totals". The calculation is ours. |
| 11:05 | Opened her file and recomputed every invoice by hand with exact decimal maths ([script](evidence/scripts/inspect_samples.py), [output](evidence/00-sample-file-inspection.txt)) | Her line amounts are all correct (quantity × price rounded to 2 decimals). What's different about the failing ones: some lines have quantity × 3-decimal price ending in half a fil, e.g. 3125 × 2.917 = **9115.625**, which she correctly rounds to 9115.63. The invoices with no such lines (0041, 0043, 0045) are exactly the ones that passed. |
| 11:10 | Read the totals code [pint.go:135-186](services/api/internal/pint/pint.go#L135-L186) | **Two different methods.** IBT-109 is the sum of her rounded line amounts (line 169), and IBT-110 is the sum of per-line rounded VAT (lines 147, 170). But IBT-112 is calculated **again from unrounded quantity × price × 1.05** (line 171), then rounded (line 184). With half-fil lines the two methods drift apart by 1–2 fils, and the ASP check ([asp-mock main.go:225-230](services/asp-mock/main.go#L225-L230)) compares in whole fils and rejects. |
| 11:15 | Ruled out the portal's own line check (AE-BR-08) | AE-BR-08 allows a 0.01 tolerance ([validate.go:155](services/api/internal/validate/validate.go#L155)), so her correctly rounded lines pass the portal, and that is what the field guide says should happen ("Item net price up to 3 decimals"). Her data is valid by our own rules. |
| 11:20 | Ruled out a VAT-rate / category issue | All lines are `S` at 5%, the same as the accepted invoices. One VAT breakdown per invoice, and it matches IBT-110, so BR-CO-14 passes. Only BR-CO-15 fails. |
| 12:20 | Reproduced: uploaded her exact file as Al Noor (seller 4) ([evidence](evidence/04-alnoor-reproduce.txt)) | Same result as her: 0041/0043/0045 **Accepted**, 0042/0044/0046 **Rejected by ASP, BR-CO-15**. Differences −0.01, −0.02, −0.01, matching my hand calculation to the fil. |
| 12:25 | Pulled the stored payload and the ASP's answer for ANF-2611-0042 | Payload totals: `taxExclusiveAmount 14307.08`, `taxAmount 715.35`, `taxInclusiveAmount 15022.42`. ASP: "Got 15022.42, expected 15022.43". 14307.08 + 715.35 = 15022.43; the portal sent 15022.42. |
| 12:30 | Replay check (`make load`) | The replay of Al Noor also shows "Accepted 3, Rejected 3" ([load output](evidence/03-make-load-output.txt)). Consistent, not a one-off. |
| 12:45 | Escalated to L3 (below) | — |
| 12:50 | Update to Fatima | — |

### Root cause

- **What happened:** For each invoice the portal calculates three totals. Two of them (total without VAT and total VAT) are built from the rounded line amounts in her file. The third (total with VAT) is calculated a different way, from unrounded quantity × price. For fuel lines priced to 3 decimals, where quantity × price ends in half a fil, the two methods disagree by 1–2 fils, and the ASP rejects the invoice under BR-CO-15.
- **Where** (component, `file:line`): api, PINT AE mapping. [services/api/internal/pint/pint.go:171](services/api/internal/pint/pint.go#L171) `gross += l.Quantity * l.UnitPrice * (1 + l.VATRate/100)`, then [pint.go:184-185](services/api/internal/pint/pint.go#L184-L185) `TaxInclusiveAmount/PayableAmount: round2(gross)`. Compare [pint.go:166-170](services/api/internal/pint/pint.go#L166-L170), where IBT-109 and IBT-110 come from rounded line values.
- **Why it happens:** IBT-112 should be IBT-109 + IBT-110 (that's literally the rule). Calculating it independently from unrounded values reintroduces rounding the other totals no longer have. It only shows when a line's quantity × price doesn't land on whole fils, which is common with 3-decimal per-litre prices and rare elsewhere. That's why "other invoices prepared the same way" passed.
- **Evidence:**
  - DB, totals per invoice ([evidence/04-alnoor-reproduce.txt](evidence/04-alnoor-reproduce.txt)):

    | Invoice | Status | IBT-109 | IBT-110 | IBT-112 sent | 109 + 110 | Diff |
    |---|---|---|---|---|---|---|
    | ANF-2611-0041 | Accepted | 13749.75 | 687.49 | 14437.24 | 14437.24 | 0.00 |
    | ANF-2611-0042 | Rejected (asp) | 14307.08 | 715.35 | 15022.42 | 15022.43 | −0.01 |
    | ANF-2611-0043 | Accepted | 18684.00 | 934.20 | 19618.20 | 19618.20 | 0.00 |
    | ANF-2611-0044 | Rejected (asp) | 11254.84 | 562.75 | 11817.57 | 11817.59 | −0.02 |
    | ANF-2611-0045 | Accepted | 11283.30 | 564.17 | 11847.47 | 11847.47 | 0.00 |
    | ANF-2611-0046 | Rejected (asp) | 5343.80 | 267.20 | 5610.99 | 5611.00 | −0.01 |

  - ASP log: `"msg":"document rejected" … "invoice_number":"ANF-2611-0042","rule":"BR-CO-15" … "Got 15022.42, expected 15022.43."` (same file).
  - Worked example, ANF-2611-0042: lines 9115.625 → 9115.63, 4748.645 → 4748.65, 442.80. Portal IBT-112 = round2((9115.625 + 4748.645 + 442.80) × 1.05) = round2(15022.4235) = **15022.42**. Correct IBT-112 = 14307.08 + 715.35 = **15022.43**.
  - Grafana: "Validation failures by rule" stays empty for these (it's not a portal rule); "ASP responses by HTTP status" shows the 422s; "Submissions by outcome" shows `rejected` — [g5-asp-responses.png](evidence/screenshots/g5-asp-responses.png) (yellow 422 bars). The invoice page for ANF-2611-0042 with the totals and the raw ASP response — [p3-alnoor-invoice-0042.png](evidence/screenshots/p3-alnoor-invoice-0042.png).
- **Confidence and open questions:** High. Predicted by hand before reproducing, and confirmed to the fil on all 6 invoices. Not done: I didn't rebuild the API with a patched line 171 to prove the fix end to end; that's for engineering. Open: how many other sellers have been hit (needs a query across all sellers for `rejected_by='asp'` with BR-CO-15; I've asked engineering to run it in production).

### Customer resolution reply OR escalation note

- **Which one and why:** **Escalation to L3**, plus an update to the customer. It's a defect in our total calculation. Support can't fix it, and there's no safe workaround on the customer's side (changing correct figures on tax invoices to dodge a check isn't acceptable, especially with an auditor involved).

#### Escalation note (sent 12:45)

```markdown
### Escalation: PINT mapping computes IBT-112 from unrounded qty×price → BR-CO-15 rejections for 3-decimal unit prices

**Priority:** P2 — 3 of 6 November invoices for Al Noor Fuel rejected by the ASP; customer's external auditor is reviewing the November VAT position and wants a written explanation. Affects any seller using 3-decimal unit prices (documented as allowed).
**Customer / seller:** Al Noor Fuel & Lubricants LLC, seller id 4 (TRN 100536284100003)
**Reported by / at:** Fatima Khoury (Finance Manager), email to support@, 10:15 Mon 16 Nov
**Affected:** import c62af631-9508-426d-a4f3-7267f833c0e2 — ANF-2611-0042, ANF-2611-0044, ANF-2611-0046 (Rejected by ASP). 0041/0043/0045 Accepted. Since: this morning's upload; likely every past upload with half-fil lines (see Ask 2).

**Symptoms (customer view):**
Invoices show "Rejected by ASP: BR-CO-15 Invoice total amount with VAT (IBT-112) must equal …". Customer's line data is correct.

**Evidence:**
- Payload excerpt (ANF-2611-0042): "totals": {"taxExclusiveAmount": 14307.08, "taxAmount": 715.35, "taxInclusiveAmount": 15022.42, "payableAmount": 15022.42}; lines netAmount 9115.63 (3125 × 2.917 = 9115.625), 4748.65 (1837 × 2.585 = 4748.645), 442.8
- ASP response: HTTP 422, rule BR-CO-15, "Got 15022.42, expected 15022.43." (0044: 11817.57 vs 11817.59; 0046: 5610.99 vs 5611.00)
- Logs: Loki {service="asp-mock"} | json | rule="BR-CO-15" → 3 lines, sender 0235:1005362841
- Metrics: invoicely_asp_responses_total{code="422"} +3; invoicely_submissions_total{outcome="rejected"} +3
- Database: SELECT invoice_number, total_excl_vat, total_vat, total_incl_vat, total_incl_vat-(total_excl_vat+total_vat) diff FROM invoices WHERE import_id='c62af631-…' → diffs -0.01 / -0.02 / -0.01 on the rejected three, 0.00 on the accepted three (full output: evidence/04-alnoor-reproduce.txt)

**Steps to reproduce:**
1. Upload samples/al-noor-fuel-nov-2026.xlsx with seller_id=4 (or `make replay CUSTOMER=al-noor`).
2. Wait ~5 s. 0042/0044/0046 → Rejected by ASP, BR-CO-15. Deterministic.

**What I have already tried / ruled out:**
- Customer data: every line passes AE-BR-08; line amounts are correct roundings of qty × price.
- VAT rate/category: all S/5%; BR-CO-14 passes; only BR-CO-15 fails.
- Not intermittent / not ASP-side: hand calculation predicted exactly which 3 fail and by how much before I reproduced it.

**Suspected cause (with confidence):** High. services/api/internal/pint/pint.go:171 accumulates gross from unrounded Quantity × UnitPrice × (1 + rate), and pint.go:184-185 sets TaxInclusiveAmount/PayableAmount = round2(gross). IBT-109 (line 169/182) and IBT-110 (line 170/183) are built from rounded line values, so the three totals are internally inconsistent whenever qty × price isn't whole fils.
Suggested fix: TaxInclusiveAmount = round2(net) + round2(vat) (and PayableAmount the same, no prepaid/rounding amounts in this model). Add a unit test with ANF-2611-0042 (expect 15022.43).

**Workaround in place:** No. Not recommending the customer change correct figures on tax invoices. Rejected invoices did not reach the buyer and do not consume their numbers, so they can be re-uploaded after the fix.

**Timeline:**
- 10:15 — email received
- 10:40 — acknowledged
- 11:05–11:20 — hand recomputation + code read, cause identified
- 12:20 — reproduced with customer file
- 12:45 — escalated

**Ask:** (1) Confirm the cause and give me a fix/deploy ETA by 16:00 today so I can give the customer a date. (2) Run in production: SELECT seller_id, count(*) FROM invoices WHERE rejected_by='asp' AND errors->0->>'rule'='BR-CO-15' GROUP BY 1; so we can tell other affected customers proactively. (3) Tell me when the fix is live; I'll ask the customer to re-upload the 3 invoices and confirm they are Accepted.
**Next customer update due:** 16:30 today
```

#### Update to the customer (sent 12:50)

> Dear Fatima,
>
> Thank you for your patience. I've completed my review, and I'm writing this so you can share it with your auditor as it is.
>
> **1. Why these invoices were rejected and the others weren't**
>
> Your figures are correct. The rejections were caused by how our portal calculated one of the invoice totals, not by anything in your file.
>
> Your file contains the invoice lines. The portal calculates the invoice totals from them: the total before VAT, the total VAT, and the total including VAT. Our network provider then checks that *total including VAT = total before VAT + total VAT*. That check is BR-CO-15.
>
> The portal calculated the total before VAT and the VAT from your line amounts, which are rounded to two decimals, as they should be. But it calculated the total including VAT a different way, from quantity × price per litre *before* rounding. For most lines that makes no difference. On some of your lines, though, quantity × price ends in half a fil. For example, 3,125 litres × AED 2.917 = AED 9,115.625, which you correctly show as 9,115.63. On those invoices our two methods ended up 1 or 2 fils apart, and the check rejected them:
>
> | Invoice | Total before VAT | VAT | Correct total incl. VAT | What our portal sent |
> |---|---|---|---|---|
> | ANF-2611-0042 | 14,307.08 | 715.35 | 15,022.43 | 15,022.42 |
> | ANF-2611-0044 | 11,254.84 | 562.75 | 11,817.59 | 11,817.57 |
> | ANF-2611-0046 | 5,343.80 | 267.20 | 5,611.00 | 5,610.99 |
>
> ANF-2611-0041, 0043 and 0045 have no half-fil lines, so the methods agreed and those invoices were accepted.
>
> **2. What you need to correct**
>
> Nothing. Please don't change your quantities, prices or line amounts; they agree with your dispatch records and with the rules for our template.
>
> **3. How and when the rejected invoices can be issued**
>
> I've passed this to our engineering team with the full details, as a fault on our side to fix. The three rejected invoices were **not issued**: they didn't reach your customers and they don't count as sent, so there's no duplicate or credit-note question for your VAT records. Their numbers are still free. Once the fix is live, I'll ask you to upload a file with just those three invoices, unchanged, and I'll confirm with you that they show as Accepted.
>
> I don't have a fix date from engineering yet, so I won't guess one. I'll update you by **16:30 today** with where it stands. If your auditor needs anything more formal, such as a signed statement or the detailed calculations, just tell me and I'll arrange it.
>
> I'm sorry for the trouble this has caused during your audit.
>
> Kind regards,
> Aakash M
> Invoicely Lite Support

### Workaround offered

None that I'd recommend. Technically the totals could be nudged by changing line amounts, but that means altering correct figures on tax invoices during an audit, which is worse than waiting. The invoices weren't issued, so nothing is lost except time. If engineering can't fix it within her deadline, the next option to discuss with L2 is a controlled data correction plus resubmission done by us, not by her.

### Prevention ideas

- **Fix the formula** so IBT-112 = IBT-109 + IBT-110 by construction (one source of truth for each amount), and do the same for the payable amount.
- **Pre-submission self-check:** run the same BR-CO-10/14/15 arithmetic in the portal before calling the ASP. If it fails, mark the invoice as our internal error (and alert), rather than letting the customer see an ASP rejection for something they can't fix.
- **Regression tests** with "awkward" data: 3-decimal prices, half-fil lines, many lines, mixed VAT categories. The al-noor sample is a perfect test case.
- **Use decimal arithmetic for money** (integer fils or a decimal type) instead of `float64` throughout the mapping.
- **Alert / dashboard:** a panel for ASP rejections by rule. A sudden BR-CO-xx rejection is almost always our bug, not the customer's, and should page L3 rather than wait for a customer email.
- **Support knowledge base:** "BR-CO-xx = calculation consistency rule. The portal calculates totals, so check our mapping first." That would have saved me the first 10 minutes.

---

## Incident 4 — `inbox/04-bluepeak-sahara-not-received.md`

### Acknowledgement

- **Sent at (exercise clock):** 11:45 (email received 11:30, P2 first-response target 12:30)
- **Reply:**

> Hi Daniel,
>
> Thanks for the detail, and for holding off on the resend. That was the right call.
>
> To confirm: your connector pushed Sahara Medical's 40-invoice batch this morning and got an HTTP 201. The invoices show "Submitted" in the portal, but many have no ASP reference, and Emirates Palm Hospital has only received a few of them.
>
> Please keep the batch on hold. If it's resent now, the portal will most likely refuse those invoice numbers as duplicates, which won't help the hospital and will make the picture harder to read.
>
> I'm checking each of the 40 invoices now, both on our side and with the network provider, to see which ones actually reached the network. I'll update you and Sahara's IT team by 13:00 with an invoice-by-invoice answer and a safe way to get the rest delivered. I don't need your connector logs yet, but I'll ask if that changes.
>
> Best regards,
> Aakash M
> Invoicely Lite Support

### Priority and justification

- **Priority:** P2 at acknowledgement. Kept at P2 after investigation, but escalated to L3 straight away and flagged as a candidate for P1 (see below).
- **Why:** A subset of invoices (26 of 40) didn't reach the buyer, so by the SLA matrix it's P2. Some invoices from this customer *are* reaching the ASP, so strictly it's not P1. What makes it urgent: (1) it's **silent**. The portal shows "Submitted" and the connector got HTTP 201, so nobody gets an error; (2) the customer **can't fix it themselves**: retry is refused (409) and a resend is rejected as duplicates; (3) the hospital's **payment run is this week**; (4) it is **systemic**. Any seller that sends more than 8 invoices in a burst is affected (scope numbers below). If the scope query had shown many sellers stuck, I'd have raised it to P1.
- **SLA deadlines I am working to:** first response by 12:30 (sent 11:45); update every 2–4 h (promised 13:00, sent 12:55; next 15:30); resolution target 8 h, i.e. by 19:30. Since that falls after business hours, I asked engineering for the data repair before 16:00 so the invoices reach the hospital today.

### Investigation log

| Time (exercise clock) | What I checked / did | What I found |
|---|---|---|
| 11:45 | Acknowledged; asked Daniel to hold the resend | — |
| 11:50 | DB: status of the 40 invoices in Sahara's import ([evidence](evidence/06-sahara-reproduce.txt)) | **14 Accepted** (with ASP reference) and **26 "Submitted" with no ASP reference and no ASP response stored**. None Failed, none Rejected. That matches what Daniel sees. |
| 11:55 | Hypothesis 1: the ASP accepted them but we lost the reply. Checked the ASP side: `GET /v1/documents?sender=0235:1006453719` | Ruled out. The ASP holds **only 14** SMS-1116 documents (001–010, 015, 020, 026, 033), all accepted. The other 26 were **never received** by the ASP, so they're not "lost in the network"; they never left properly. |
| 12:00 | API log: the ASP responses for this batch | `"msg":"asp response" … "status_code":429` **26 times**, `200` 14 times. HTTP 429 = "Too Many Requests". |
| 12:02 | ASP log | 26 × `"msg":"rate limit exceeded","sender":"0235:1006453719","retry_after_s":1`. The ASP's fair-use limit ([architecture.md → ASP integration](docs/architecture.md#asp-integration)) is a burst of 8, then 2 per second per sender ([asp-mock main.go:35-37](services/asp-mock/main.go#L35-L37)). Our 4 submission workers send the 40 much faster than that. The docs say a 429 means *"the document has not been received and should be sent again later"*. |
| 12:05 | Code: how does the portal handle a 429? [submit.go:114](services/api/internal/submit/submit.go#L114), [submit.go:133-155](services/api/internal/submit/submit.go#L133-L155) | **Root cause.** The status is set to `Submitted` *before* calling the ASP (line 114). The `switch` on the response handles 200, 422 and 500/502/503/504, but **has no case for 429**. So nothing happens: no Failed status, no retry, no error, no event. The invoice stays "Submitted" forever. |
| 12:08 | Status history of a stuck invoice (SMS-1116-011) | `Parsed 04:30:17 → Validated 04:30:21 → Submitted 04:30:37` and nothing after. |
| 12:10 | Hypothesis 2: support or the customer can use the documented Retry | Ruled out. `POST /v1/invoices/{id}/retry` → **HTTP 409** "only invoices in status Validated or Failed can be retried (current status: Submitted)" ([httpapi.go:270](services/api/internal/httpapi/httpapi.go#L270)); batch retry → `{"requeued":0}`. |
| 12:15 | What if Daniel resends the batch? (Tested in the lab only) | **All 40 rejected** with AE-BR-09, *"already exists for this seller with status 'Submitted'"* (or 'Accepted'). Resending can't deliver the 26 either. Holding off was right, and it means only engineering can unblock them. |
| 12:20 | Why didn't monitoring catch it? `/metrics` | `invoicely_asp_responses_total{code="429"} 26`, but `invoicely_submissions_total` only has `accepted / rejected / failed`. Throttled sends aren't counted at all, so the "Submissions by outcome" panel looks healthy. Only "ASP responses by HTTP status" shows the 429s. |
| 12:25 | Replay check (`make load`) | The replayed Sahara batch: "Submitted 30, Accepted 10". Same failure, slightly different split (timing-dependent). |
| 12:30 | Scope: all invoices stuck in Submitted without an ASP reference, by seller ([evidence](evidence/09-scope-queries.txt)) | See Evidence below. |
| 12:40 | Escalated to L3 (P2) | — |
| 12:55 | Update to Daniel and Sahara IT | — |

### Root cause

- **What happened:** The ASP only accepts 8 documents at once from one sender, then 2 per second. Sahara's 40 invoices were sent faster than that, so the ASP answered "429 Too Many Requests, try again in 1 second" for 26 of them. Our portal doesn't handle that answer at all: it had already marked them "Submitted" and never retries, marks them failed, or tells anyone. Those 26 invoices never reached the ASP, so they never reached Emirates Palm Hospital.
- **Where** (component, `file:line`): api, submission worker. [services/api/internal/submit/submit.go:133-155](services/api/internal/submit/submit.go#L133-L155) (no `case http.StatusTooManyRequests`), with [submit.go:114](services/api/internal/submit/submit.go#L114) setting `Submitted` before the call. No client-side pacing per sender ([submit.go:56-91](services/api/internal/submit/submit.go#L56-L91), 4 workers pulling as fast as they can). Retry is blocked for `Submitted` at [httpapi.go:270](services/api/internal/httpapi/httpapi.go#L270) and [store.go:368-369](services/api/internal/store/store.go#L368-L369).
- **Why it happens:** The ASP's rate limit is documented, but the integration was written as if every response were 200, 422 or 5xx. Small batches (≤ 8 invoices) never notice, and big batches from ERP connectors always do.
- **Evidence** (all in [evidence/06-sahara-reproduce.txt](evidence/06-sahara-reproduce.txt)):
  - DB: `Accepted | has_asp_reference t | 14` · `Submitted | has_asp_reference f | 26`
  - API log: `asp response status codes for SMS-1116-*: {200: 14, 429: 26}`
  - ASP log: `{"level":"WARN","msg":"rate limit exceeded","sender":"0235:1006453719","retry_after_s":1}` ×26
  - ASP's own list for the sender: 14 documents received, all accepted
  - Retry: `HTTP 409 {"error":"only invoices in status Validated or Failed can be retried (current status: Submitted)"}`
  - Resend test: 40 × Rejected AE-BR-09
  - Metrics: `invoicely_asp_responses_total{code="429"} 26` vs `invoicely_submissions_total` without a throttled outcome; ASP side `asp_documents_total{outcome="throttled"} 26`
  - Scope across all sellers after the morning replay: [evidence/09-scope-queries.txt](evidence/09-scope-queries.txt)
  - Grafana "ASP responses by HTTP status": blue **HTTP 429** bars — [g5-asp-responses.png](evidence/screenshots/g5-asp-responses.png). My first Sahara upload's 26 × 429 don't show as a bar at all: most likely because the 429 counter series was brand new and `increase()` ignores a series' first sample. The first burst of throttling is invisible on the dashboard.
  - Portal batch page: **Submitted 26 / Accepted 14** — [p2-sahara-batch.png](evidence/screenshots/p2-sahara-batch.png)
- **Confidence and open questions:** High. Reproduced with the customer's file, cause visible in code, logs and the ASP's own records. Open: in production, I'd confirm with the real ASP that it really has no record of the 26 (in the lab, the mock's document list is in memory and is cleared if the mock restarts). I'd also ask whether the ASP can raise Sahara's fair-use limit as a short-term measure.

### Customer resolution reply OR escalation note

- **Which one and why:** **Escalation to L3**, plus an update to Daniel and Sahara. It's a product defect, and the fix for the 26 stuck invoices is a **data repair** (their status has to be reset so they can be resubmitted), which support can't do through the product. The escalation policy calls for L3 in exactly this case.

#### Escalation note (sent 12:40)

```markdown
### Escalation: ASP HTTP 429 not handled — invoices stuck in "Submitted" forever, never delivered, not retryable

**Priority:** P2 (candidate P1) — 26 of 40 Sahara Medical invoices never reached the ASP; silent (portal says Submitted, connector got 201); customer cannot retry or resend; buyer's payment run this week. Systemic: any seller sending > 8 invoices in a burst.
**Customer / seller:** Sahara Medical Supplies FZE, seller id 5 (Peppol 0235:1006453719), via Bluepeak ERP connector
**Reported by / at:** Daniel Okafor (Bluepeak ERP Integrations), email, 11:30 Mon 16 Nov; cc it@saharamedical
**Affected:** import 2b4feddf-a863-40e0-ab54-f03da5785cdc — 26 invoices in status Submitted with asp_message_id = '' (SMS-1116-011..014, 016..019, 021..025, 027..032, 034..040). Other sellers: see scope query in evidence/09-scope-queries.txt.

**Symptoms (customer view):**
Invoices show "Submitted", ASP reference empty; buyer (Emirates Palm Hospital, 0235:…) received only 14 of 40.

**Evidence:**
- API log: {"msg":"asp response","invoice_number":"SMS-1116-011","status_code":429,…} ×26; 200 ×14
- ASP log: {"level":"WARN","msg":"rate limit exceeded","sender":"0235:1006453719","retry_after_s":1} ×26
- ASP GET /v1/documents?sender=0235:1006453719 → 14 SMS-1116 documents, all accepted; the 26 are absent
- DB: SELECT status, asp_message_id<>'' , count(*) FROM invoices WHERE import_id='2b4feddf-…' GROUP BY 1,2 → Accepted/t/14, Submitted/f/26; invoice_events for SMS-1116-011 end at "Submitted 04:30:37"
- POST /v1/invoices/{id}/retry → 409 (status Submitted); POST /v1/imports/{id}/retry → requeued 0
- Metrics: invoicely_asp_responses_total{code="429"}=26 but no matching invoicely_submissions_total outcome

**Steps to reproduce:**
1. curl -F file=@samples/sahara-medical-batch-1116.xlsx -F seller_id=5 http://localhost:8080/v1/imports (or `make replay CUSTOMER=sahara`)
2. Wait 30 s → ~14 Accepted, ~26 Submitted with empty ASP reference (split varies with timing).

**What I have already tried / ruled out:**
- Not an ASP-side loss: the ASP never received the 26 (its own list).
- Not the connector: hand-off got 201; the issue is after import.
- Retry: blocked (409). Resend: all 40 rejected AE-BR-09 (tested in lab) — customer asked NOT to resend.

**Suspected cause (with confidence):** High. services/api/internal/submit/submit.go:133-155 — switch on ASP status has no case for 429; status was already set to Submitted at submit.go:114, so the invoice is left in Submitted with no event, no error, no retry. No per-sender pacing in the worker pool (4 workers) vs ASP limit of burst 8 + 2/s (asp-mock main.go:35-37).

**Workaround in place:** No customer-side workaround. Customer told to hold the resend.

**Timeline:**
- 11:30 email · 11:45 ack · 11:50–12:10 DB/ASP/log/code analysis · 12:15 resend test (lab) · 12:30 scope query · 12:40 this escalation

**Ask:**
1. TODAY, before 16:00 — data repair: for invoices with status='Submitted' AND asp_message_id='' AND updated_at < now()-interval '5 min', and confirmed absent on the ASP side, set status='Failed' (with an invoice_events row "Reset after unhandled ASP 429") so the documented Retry works; then resubmit them paced (≤ 2/s per sender). Start with Sahara's 26 so they reach the hospital before its payment run.
2. Code fix: handle 429 in submit.go — honour Retry-After, put the invoice back on the queue (or mark Failed with a clear reason), and add per-sender client-side rate limiting; add outcome="throttled" to invoicely_submissions_total.
3. Alert: invoices in Submitted > 5 min without an ASP reference.
Please confirm owner + ETA for (1) by 14:00.
**Next customer update due:** 15:30 today
```

#### Update to the customer (sent 12:55)

> Hi Daniel (and Sahara IT team),
>
> Thanks for waiting. Here's where things stand.
>
> **1. Is Invoicely losing invoices? Where are the rest?**
>
> Nothing has been lost, but 26 of the 40 invoices haven't been delivered yet. I'm sorry; the cause is on our side.
>
> - **Delivered (14):** SMS-1116-001 to 010, 015, 020, 026 and 033. These have an ASP reference in the portal, and our network provider confirms it has them.
> - **Not delivered (26):** all the others. They're safely stored in our portal with all their data, but they never reached the network provider, so the hospital couldn't have received them.
>
> What happened: our network provider accepts invoices from one company at a limited speed. When a large batch arrives all at once, it asks the sender to "slow down and try again in a second". Our portal didn't handle that request properly. It left those invoices showing "Submitted" instead of trying again. So your connector did everything right, the 201 response was correct, and nothing would have shown in your logs.
>
> **2. Should you resend the batch?**
>
> No, please don't. I tested it, and the portal would refuse all 40 as duplicates of invoices it already holds, so a resend wouldn't get the 26 through.
>
> **What happens next:** I've escalated this to our engineering team as a priority. They will release the 26 invoices and send them at a pace the network accepts. I've asked for this to be done this afternoon so the hospital has them before its payment run. You don't need to do anything. When they're through, I'll send you and Sahara the list with an ASP reference for each one, so you can confirm with the hospital.
>
> I'll update you by **15:30 today**, whether or not it's finished by then.
>
> Engineering is also fixing the underlying problem so larger batches go through without this. Until that's in place, if your connector can send Sahara's invoices in smaller batches (8 or fewer per push, a few seconds apart), that will avoid it happening again.
>
> Best regards,
> Aakash M
> Invoicely Lite Support

### Workaround offered

- **For the 26 stuck invoices:** none on the customer side (retry → 409, resend → AE-BR-09). They need the L3 data repair, then a paced resubmission.
- **Until the code fix:** ask the connector to push ≤ 8 invoices per request with a few seconds between pushes, so the ASP limit is never hit. I'd confirm this with engineering first, because other sellers' traffic doesn't share Sahara's limit, but Sahara's own parallel pushes do.

### Prevention ideas

- **Handle 429 properly:** honour `Retry-After`, requeue, and never leave an invoice in `Submitted` without a final outcome.
- **Client-side pacing per sender** that matches the ASP's published fair-use policy (burst 8, 2/s), instead of relying on the ASP to push back.
- **Set `Submitted` only after a definite answer**, or add a reconciliation job: any `Submitted` without an ASP reference after N minutes → check the ASP's document list → mark `Failed` (retryable) or `Accepted`.
- **Observability:** add `outcome="throttled"` to `invoicely_submissions_total`; alert on 429s; add a dashboard stat "invoices stuck in Submitted > 5 min".
- **Make the API response honest for integrators:** the 201 means "file received and validated", not "delivered". Document that, and give connectors a status endpoint or webhook for the final outcome.
- **Support runbook:** "Submitted with no ASP reference = check `asp_responses_total{code="429"}` and the ASP's document list before anything else."

---

## Incident 5 — `inbox/05-ghaf-cafe-date-error.md`

### Acknowledgement

- **Sent at (exercise clock):** 12:25 (email received 12:10, P3 first-response target 16:10; I replied early because the fix is quick and she is blocked)
- **Reply:**

> Hello Hessa,
>
> Thank you for getting in touch, and I'm sorry this has held up your invoices.
>
> I can see that all four invoices in your file were stopped with a message about the date "13/11/2026". You're right that 13/11/2026 is the 13th of November. The portal stops dates written as text in that form on purpose, because some systems would read 05/11/2026 as 11 May. For tax invoices it doesn't guess.
>
> The good news is that nothing was sent with a wrong date, and this is quick to fix in your Excel file. I'm checking your file now and will send you the exact steps (about two minutes of work) by 14:00 today.
>
> Kind regards,
> Aakash M
> Invoicely Lite Support

### Priority and justification

- **Priority:** P3
- **Why:** One customer and one cause. The product is behaving exactly as documented (the template field guide says text dates like `13/11/2026` are rejected with AE-BR-04), and there's a simple fix on her side. By the SLA matrix's last question ("working as documented?") this could be P4. I kept it at P3 because she is completely blocked (0 of 4 invoices sent), her customers are waiting, and she's upset, so it deserved a same-day answer rather than "1 business day". It isn't P2: nothing is broken, and no other customer is affected by her file.
- **SLA deadlines I am working to:** first response by 16:10 (sent 12:25); resolution target 3 days, but I aimed for today (steps sent 13:40, before the 14:00 I promised); update cadence daily, so if she hasn't confirmed by tomorrow morning I check her imports myself and follow up.

### Investigation log

| Time (exercise clock) | What I checked / did | What I found |
|---|---|---|
| 12:15 | Read the email and the error text | The error names the rule (AE-BR-04) and the exact value `'13/11/2026'`. That points at the date format, not a system fault. |
| 12:20 | Looked up AE-BR-04 in `docs/template-field-guide.md` | Documented behaviour: dates must be `YYYY-MM-DD` text or real Excel date cells; `13/11/2026` / `11/13/2026` as text are rejected on purpose because they are ambiguous. |
| 12:25 | Sent acknowledgement | — |
| 12:30 | Opened her attachment and checked the cell types of both date columns ([script](evidence/scripts/inspect_samples.py), [output](evidence/00-sample-file-inspection.txt)) | All 16 date cells are **text** (`cell_type=s`, format `General`), typed by hand. They are not real Excel dates. |
| 12:35 | Hypothesis: maybe her cells are real dates and the portal reads them wrongly (that would be our bug). Checked the code. | Ruled out. [sheet.go:97](services/api/internal/sheet/sheet.go#L97) reads raw cell values, so a real date arrives as a serial number, and [sheet.go:171-186](services/api/internal/sheet/sheet.go#L171-L186) accepts ISO text or serial numbers. Her text values fail both, and [validate.go:116](services/api/internal/validate/validate.go#L116) raises AE-BR-04. Works as designed. |
| 12:45 | Reproduced: uploaded her file as Ghaf Tree Café (seller 6) ([evidence](evidence/05-ghaf-reproduce.txt)) | 4 of 4 invoices Rejected by portal. The **only** rule hit is AE-BR-04 on `Invoice issue date*` and `Payment due date*`. No other problems hiding behind it. |
| 13:00 | Fix 1: converted the dates to `YYYY-MM-DD` text ([script](evidence/scripts/fix_ghaf_dates.py)) and uploaded with the **same invoice numbers** | All 4 **Accepted** with ASP references (GTC-118 to GTC-121). Confirms a rejected invoice doesn't "use up" its number. |
| 13:15 | Fix 2: real Excel date cells **displayed** as dd/mm/yyyy, i.e. what Excel's Text to Columns produces ([script](evidence/scripts/ghaf_real_dates_test.py)). Test invoice numbers (`TEST-…`) so nothing clashes | All 4 **Accepted**, dates read correctly as 2026-11-13 etc. So she can keep *seeing* dates the way she likes, as long as Excel stores them as dates. |
| 13:40 | Sent resolution reply | — |

Note: in the lab I uploaded her corrected file myself to prove the fix. On a real shift I would **not** submit tax invoices on a customer's behalf. I'd test with a copy under test invoice numbers only, and let her upload. In the lab, GTC-118 to GTC-121 are now Accepted from my test, so I've written the reply as if she uploads.

### Root cause

- **What happened:** The issue and due dates in her file are typed as text in day/month/year form (`13/11/2026`). The portal only accepts `YYYY-MM-DD` text or real Excel date cells, so every invoice was rejected at upload with AE-BR-04 and none were sent.
- **Where** (component, `file:line`): api, template parsing and validation. [sheet.go:171-186](services/api/internal/sheet/sheet.go#L171-L186) (`ParseDate` accepts ISO or Excel serial only) and [validate.go:116](services/api/internal/validate/validate.go#L116) (AE-BR-04 error). Documented in [template-field-guide.md → Dates](docs/template-field-guide.md#dates).
- **Why it happens:** It's a deliberate rule. `05/11/2026` means 5 November in the UAE and 11 May in the US, and the portal must not guess the date on a tax invoice. Her Excel stored what she typed as text because it wasn't entered as a date (format "General").
- **Evidence:** [evidence/05-ghaf-reproduce.txt](evidence/05-ghaf-reproduce.txt) (DB query: 4 × Rejected, AE-BR-04 only; corrected file: 4 × Accepted with ASP references; real-date-cell test: 4 × Accepted); [evidence/00-sample-file-inspection.txt](evidence/00-sample-file-inspection.txt) (cell types); portal batch page with 4 × Rejected and the dates as typed — [p4-ghaf-batch.png](evidence/screenshots/p4-ghaf-batch.png).
- **Confidence and open questions:** High. Reproduced with her exact file, and fixed by changing only the date cells. One open question: did she use the official template's `Instructions` sheet? If she started from a blank sheet, that may explain why she didn't know about the date format.

### Customer resolution reply OR escalation note

- **Which one and why:** Resolution reply, **no escalation.** The product works as documented (escalation policy: "Do not escalate when the product is working as documented"). I raise the confusing error message as a product suggestion instead (see Prevention).

> Hello Hessa,
>
> As promised, here is what happened and how to fix it.
>
> **What happened:** your dates are right. The problem is that Excel stored them as text (the words "13/11/2026") instead of as dates. When a date is only text, the portal can't safely tell whether 05/11/2026 means 5 November or 11 May, so for tax invoices it refuses to guess and stops the invoice. That's why all four were rejected. None of them were sent, so nothing went out with a wrong date.
>
> **How to fix it (about two minutes):**
>
> 1. Open your file and click the column letter above **Invoice issue date**.
> 2. Go to **Data → Text to Columns**, click **Next**, **Next**, then choose **Date: DMY** and click **Finish**. The dates will now line up on the right of the cell, which means Excel sees them as real dates.
> 3. Do the same for the **Payment due date** column.
> 4. Save the file and upload it again for Ghaf Tree Café.
>
> You can keep seeing the dates as 13/11/2026; you don't need to change how they look. You can also type them as 2026-11-13 if you prefer.
>
> You can upload the same four invoice numbers (GTC-118 to GTC-121) again. Rejected invoices are never issued, so the numbers are still free.
>
> **How to check it worked:** on the batch page all four invoices should show **Accepted**, each with an "ASP reference". That means they're on their way to your customers.
>
> I tested these steps on a copy of your file and all four invoices passed. If anything still doesn't look right, reply here and I'll check it straight away.
>
> We're also looking at making this error message clearer, so it tells you how to fix the date rather than just what's wrong. Thank you for raising it.
>
> Kind regards,
> Aakash M
> Invoicely Lite Support

### Workaround offered

None needed, because this is the fix: convert the two date columns to real dates (Text to Columns → DMY) or to `YYYY-MM-DD`, then re-upload with the same invoice numbers.

### Prevention ideas

- **Clearer error message** (product suggestion, not an incident): AE-BR-04 says what's wrong but not how to fix it. Something like *"'13/11/2026' is text, not a date. In Excel use Data → Text to Columns → DMY, or type 2026-11-13"*, plus a link to the field guide.
- **Template hardening:** ship the official template with the date columns pre-formatted as Date and with Excel data validation (Date type), so a typed date becomes a real date from the start.
- **Optional per-seller date setting:** let a seller declare "my text dates are DMY" at onboarding. Then `13/11/2026` is no longer ambiguous for that seller and the portal isn't guessing. This needs a product decision; it isn't something support can change.
- **Support macro / help article** for AE-BR-04 with the Text to Columns steps and screenshots. This is probably a common first-upload issue for small customers.

---

## Overall

### Prioritisation

| Order worked | Item | Priority | Received | First response | Main reason |
|---|---|---|---|---|---|
| 1 | #2 API restarts / 502s | **P1** | 09:42 (alert), 09:50 (CSM) | 09:45 on-call, 09:55 CSM | Production-wide; invoices not reaching the ASP; go-live Wed |
| 2 | #1 Oasis upload stuck | P2 | 09:05 | 09:15 | Month-end; customer doesn't know what was issued; duplicate risk |
| 3 | #4 Sahara not received | P2 (candidate P1) | 11:30 | 11:45 | Silent non-delivery; customer can't self-fix; payment run |
| 4 | #3 Al Noor BR-CO-15 | P2 | 10:15 | 10:40 | 3 of 6 rejected; auditor; turned out to be our calculation |
| 5 | #5 Ghaf date error | P3 | 12:10 | 12:25 | One customer; works as documented; simple fix |

**Did I change my mind?**

- **Oasis.** I started it at 09:15 as the only item in the queue. I dropped it the moment the P1 alert came in, then came back to it at 10:10 because the customer's question ("what has been sent?") was answerable from the database in minutes. It would have been wrong to let a P1 swallow an easy, promised answer. After I confirmed all 8 invoices were delivered once, I treated the rest of Oasis as a **P3 bug**, not an ongoing P2.
- **Sahara.** I nearly raised it to P1, because it's silent and affects any large batch. I kept it at P2 only after the scope query showed Sahara was the only seller affected that morning. I'd have raised it immediately if other sellers had shown stuck "Submitted" invoices.
- **Al Noor.** It stayed P2, but the nature changed: I first expected a customer-data issue (rounding in their file), and the evidence showed it was our mapping. That changed it from "help the customer fix their file" to "escalate a defect and tell them not to change anything".
- **Ghaf.** On the SLA guide alone it could be P4 (working as documented). I kept it P3 because she was completely blocked and upset, and the fix was quick.
- **Links between items.** I checked whether #1 and #2 were the same incident (they aren't, but large Oasis uploads add a lot to the API's memory and a restart mid-import would make Oasis's situation much worse), and whether #4 affects Marina Bay's go-live (only if they send > 8 invoices at once, so I flagged it to Priya).

### What I would do differently

- **Check the lab machine's capacity first.** My laptop has 6 GB of RAM in total. Docker got ~2.8 GB, and during the replay the whole machine started swapping and Docker stopped responding for a few minutes. I had to stop the replay at 175/240 uploads and separate "product" symptoms from "my laptop" symptoms (lookup timeouts). Next time I'd close everything else first and give Docker 4 GB+.
- **Don't trust an alert's number without a second source.** I'd have reported "3 restarts" to engineering if I hadn't checked `docker events`. The restart alert can fire with zero real restarts (clock drift). Lesson: always confirm an alert against the raw signal.
- **Ask the customer for exact times earlier.** For Oasis, his upload times would have let me match his three attempts to the three imports immediately, instead of inferring from the database.
- **Run scope queries earlier.** I ran the "which other sellers are affected?" queries after writing the escalations. They should come before deciding priority, because they decide P1 vs P2.
- **Testing on behalf of a customer.** In the lab I uploaded Ghaf's corrected file under her real invoice numbers to prove the fix. On a real shift I'd only test on a copy with test invoice numbers and let the customer issue her own tax invoices.

### What I learned / what I would need to learn

Concepts this shift relied on, how I got up to speed on each, and what I'd study next:

- **UAE e-invoicing / Peppol:** the 5-corner model (seller → ASP → buyer's ASP → buyer, plus FTA reporting), PINT AE, the TRN and participant id formats, and the difference between portal rules (AE-BR-xx: customer data) and ASP rules (BR-CO-xx: totals consistency). The key insight: **BR-CO-xx failures are almost always about how *we* calculated totals**, because the customer doesn't supply totals. I learned this from `docs/architecture.md` and `docs/template-field-guide.md`, then confirmed it in `pint.go` and `asp-mock`.
- **HTTP 429 / rate limits:** a 429 isn't an error to log and forget; it means "not received, send later" (with `Retry-After`). An integration has to treat it as a state.
- **Containers and memory:** exit code 137 = SIGKILL (OOM killer); `docker events` shows `oom`/`die`/`start`; `MemorySwap == Memory` means no swap. A memory graph that only goes up between restarts means *retention*, not load.
- **Prometheus and Grafana:** `changes()` on `process_start_time_seconds` is fragile in VMs; an API can't report its own 5xx when it's dead (the proxy's 502s are invisible to it); and the difference between `up`, heap and working-set memory.
- **Go service internals as a support engineer:** an in-memory channel queue disappears on restart; an import that inserts rows before validating them creates a window where other requests see half-finished data (the Oasis race); and logging a warning instead of failing can silently skip a business check (AE-BR-11).
- **What I'd study next:** the PINT AE specification and the UAE FTA e-invoicing timeline; PromQL beyond the basics (writing robust alert expressions); Go memory profiling (`pprof`), to prove the cache theory directly; and idempotency patterns for upload APIs (file hashes, idempotency keys), which would remove the Oasis and Sahara duplicate dilemmas entirely.

### Time log (real time)

All times are India Standard Time (UTC+5:30), 14 November 2026.

| Date | From–to | What I worked on |
|---|---|---|
| 14 Nov 2026 | 09:05–09:21 | Read INSTRUCTIONS, START_HERE and the SUBMISSION template; cloned the repo |
| 14 Nov 2026 | 09:21–09:55 | Setup: started Docker Desktop, removed old unused containers/images to free space, first `docker compose up --build` (about 30 min on my machine: 6 GB RAM, so builds were slow). Meanwhile read docs, inbox and code, inspected the sample files, drafted acknowledgements |
| 14 Nov 2026 | 09:55–10:35 | Reproduced all five items: baseline upload, Ghaf, Al Noor, Sahara, Oasis via the portal, `make load` replay with memory/OOM capture |
| 14 Nov 2026 | 10:20–10:35 | Docker froze under the replay (host out of RAM); diagnosed it, stopped the replay at 175/240 |
| 14 Nov 2026 | 10:30–10:50 | Scope queries, Incident 2 workaround test, Prometheus export, alert-state analysis; write-up of all five incidents |
| 14 Nov 2026 | 10:50–11:30 | Evidence index, link/line-reference check, overall section, publishing to GitHub |

### AI usage disclosure

- **Tool:** Claude Code (Anthropic, model Claude Opus 5.5) running in VS Code, with access to my terminal and Docker.
- **How I used it:** I used it as a hands-on assistant for most of this assignment.
  - It read the docs and code and proposed the likely root causes.
  - It ran the Docker, curl, SQL and Prometheus commands that produced everything in `evidence/`, and wrote the helper scripts in `evidence/scripts/`.
  - It drafted the acknowledgements, customer replies, escalation notes and this document.
  - My part: directing the work, making the setup decisions (cleaning up Docker, stopping the replay when my laptop ran out of memory, the GitHub repo), and reviewing the submission.
- **How the output was checked against the system:**
  - **No root cause rests on reading code alone.** Each one was reproduced on the running lab with the customer's own file, and the evidence files show the exact commands and their real output.
  - The Al Noor totals were predicted by hand calculation *before* the upload, and the system matched them to the fil.
  - The Sahara 429s appear in three independent places: the API log, the ASP log, and the ASP's own document list.
  - The OOM kills appear in `docker events` with exit code 137.
  - Where a first reading was wrong or incomplete, the system corrected it:
    - The restart alert count looked authoritative, but `docker events` showed it over-counts (it fired before any real restart).
    - An evidence note had "8 buyers"; the file has 5, now fixed.
    - Lookup timeouts during my laptop's memory starvation were excluded as environment noise, not product behaviour.
  - Every `file:line` reference in this document was checked by printing the cited line, and every link was checked to resolve.
