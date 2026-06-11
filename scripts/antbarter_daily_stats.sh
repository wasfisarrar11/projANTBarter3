#!/usr/bin/env bash
# AntBarter daily stats — run on the Azure VM.
#
# Usage:
#   chmod +x scripts/antbarter_daily_stats.sh
#   ./scripts/antbarter_daily_stats.sh
#
# Assumes SQLite at ~/AntBarter-AI-Test/src/backend/python/antbarter_local.db.
# If you move to Azure SQL later, swap the sqlite3 calls for sqlcmd.
set -euo pipefail

DB="${ANTBARTER_DB:-$HOME/AntBarter-AI-Test/src/backend/python/antbarter_local.db}"

if [[ ! -f "$DB" ]]; then
  echo "Database not found at $DB" >&2
  echo "Set ANTBARTER_DB=/path/to/antbarter_local.db to override." >&2
  exit 1
fi

echo "=== AntBarter daily stats — $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
echo

echo "-- Chat volume by day (last 14 days) --"
sqlite3 -header -column "$DB" "
SELECT date(created_at) AS day, COUNT(*) AS sessions
FROM negotiation_sessions
WHERE created_at >= date('now', '-14 day')
GROUP BY day
ORDER BY day DESC;
"
echo

echo "-- Active subscribers --"
sqlite3 -header -column "$DB" "
SELECT status, COUNT(*) AS users
FROM subscriptions
GROUP BY status
ORDER BY users DESC;
"
echo

echo "-- New negotiation sessions today --"
sqlite3 "$DB" "
SELECT COUNT(*) FROM negotiation_sessions
WHERE date(created_at) = date('now');
"
echo

echo "-- Refusals in the last 24h (top categories) --"
# api_usage table doesn't track refusals; refusals live in the negotiation
# session's messages_json. This is a quick heuristic, not a perfect counter.
sqlite3 -header -column "$DB" "
SELECT
  CASE WHEN messages_json LIKE '%\"blocked\": true%' THEN 'blocked' ELSE 'ok' END AS status,
  COUNT(*) AS n
FROM negotiation_sessions
WHERE created_at >= datetime('now', '-1 day')
GROUP BY status;
"
echo

echo "-- API calls by endpoint (last 24h) --"
sqlite3 -header -column "$DB" "
SELECT endpoint, COUNT(*) AS calls, COALESCE(SUM(estimated_tokens), 0) AS est_tokens
FROM api_usage
WHERE created_at >= datetime('now', '-1 day')
GROUP BY endpoint
ORDER BY calls DESC;
"
