#!/usr/bin/env bash
# Run a SQL query against the lab database and print it with its output.
# usage: evidence/scripts/q.sh "SELECT ..."
echo "invoicely=# $1"
docker compose exec -T postgres psql -U invoicely -d invoicely -P pager=off -c "$1"
