"""Query Prometheus range data and print a compact table (one row per minute)."""
import json, sys, urllib.parse, urllib.request, datetime
BASE = "http://localhost:9090/api/v1/query_range"
def q(expr, start, end, step="30s"):
    url = BASE + "?" + urllib.parse.urlencode({"query": expr, "start": start, "end": end, "step": step})
    return json.load(urllib.request.urlopen(url))["data"]["result"]
start, end = sys.argv[1], sys.argv[2]
series = {
  "api_mem_MiB": 'max(container_memory_working_set_bytes{container_label_com_docker_compose_service="api"})/1048576',
  "api_heap_MiB": 'go_memstats_heap_inuse_bytes{job="api"}/1048576',
  "api_up": 'up{job="api"}',
  "restarts_15m": 'changes(process_start_time_seconds{job="api"}[15m])',
  "queue_depth": 'invoicely_submission_queue_depth',
}
data = {}
for name, expr in series.items():
    for r in q(expr, start, end):
        for ts, v in r["values"]:
            data.setdefault(int(ts), {})[name] = float(v)
print("# Prometheus query_range", start, "->", end, "step 30s")
for name, expr in series.items(): print(f"#  {name:13} = {expr}")
print(f"{'time_utc':9} " + " ".join(f"{n:>13}" for n in series))
for ts in sorted(data):
    row = data[ts]
    print(datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%H:%M:%S") + " " +
          " ".join(f"{row[n]:13.1f}" if n in row else f"{'-':>13}" for n in series))
