#!/usr/bin/env bash
# Scope queries across ALL sellers, run after `make load` (the morning replay).
Q="$(dirname "$0")/q.sh"
echo "### Run at $(date -u +%FT%TZ)"
echo; echo "## 1. Invoices not in a final state, by seller and status (older than 5 minutes)"
$Q "SELECT s.name, v.status, (v.asp_message_id<>'') AS has_asp_ref, count(*), to_char(min(v.updated_at),'HH24:MI:SS') AS stuck_since FROM invoices v JOIN sellers s ON s.id=v.seller_id WHERE v.status IN ('Parsed','Validated','Submitted','Failed') AND v.updated_at < now()-interval '5 minutes' GROUP BY 1,2,3 ORDER BY 1,2;"
echo; echo "## 2. Imports that never finished (stuck in Processing)"
$Q "SELECT s.name, i.filename, i.status, to_char(i.created_at,'HH24:MI:SS') AS created, (SELECT jsonb_object_agg(status,n) FROM (SELECT status,count(*) n FROM invoices v WHERE v.import_id=i.id GROUP BY status) c) AS invoices FROM imports i JOIN sellers s ON s.id=i.seller_id WHERE i.status IN ('Uploaded','Processing') ORDER BY i.created_at;"
echo; echo "## 3. Marina Bay Hospitality (seller 3) this morning: imports and invoice outcomes"
$Q "SELECT i.status AS import_status, count(DISTINCT i.id) AS imports, count(v.id) AS invoices, count(v.id) FILTER (WHERE v.status='Accepted') AS accepted, count(v.id) FILTER (WHERE v.status IN ('Parsed','Validated')) AS stuck_parsed_or_validated, count(v.id) FILTER (WHERE v.status='Submitted' AND v.asp_message_id='') AS stuck_submitted FROM imports i LEFT JOIN invoices v ON v.import_id=i.id WHERE i.seller_id=3 AND i.created_at > now()-interval '3 hours' GROUP BY 1;"
echo; echo "## 4. ASP rejections by rule and seller"
$Q "SELECT s.name, v.errors->0->>'rule' AS rule, count(*) FROM invoices v JOIN sellers s ON s.id=v.seller_id WHERE v.rejected_by='asp' GROUP BY 1,2 ORDER BY 3 DESC;"
echo; echo "## 5. Submitted without ASP reference = unhandled HTTP 429 (Incident 4), by seller"
$Q "SELECT s.name, count(*) FROM invoices v JOIN sellers s ON s.id=v.seller_id WHERE v.status='Submitted' AND v.asp_message_id='' GROUP BY 1 ORDER BY 2 DESC;"
echo; echo "## 6. ASP side: throttled (429) documents per sender (asp-mock log)"
docker compose logs asp-mock --no-log-prefix 2>/dev/null | grep '"rate limit exceeded"' | grep -o '"sender":"[^"]*"' | sort | uniq -c
