# Error Patterns — WA Monitor

Each pattern has a diagnostic command, expected output, and step-by-step fix.

---

## QR_NOT_SHOWING

**Symptoms**: Onboarding page loads but no QR code appears, or QR loads then immediately disappears.

**Diagnostic**:
```bash
# Check if WAHA is responding (replace WAHA_PUBLIC_URL with the Railway public URL for the WAHA service)
curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  -H "X-Api-Key: WAHA_API_KEY" \
  "https://WAHA_PUBLIC_URL/api/sessions"
```
- 200 → WAHA is up; issue is the Node.js app cannot reach it internally
- Non-200 or timeout → WAHA service is down

**Fix**:
1. Railway → WAHA service → Variables → confirm `WHATSAPP_DEFAULT_ENGINE` = `NOWEB`
2. Railway → Node.js service → Variables → confirm `WAHA_BASE_URL` = exactly `http://waha.railway.internal:3000` (internal URL — NOT the public Railway URL)
3. If `WAHA_BASE_URL` was wrong → update it → Railway auto-redeploys → wait 90 seconds → retry

**Verification**: Open the app URL and go through onboarding. QR should appear within 5 seconds.

---

## MESSAGES_NOT_CAPTURED

**Symptoms**: WhatsApp shows "Linked" / "Connected" but messages sent to the group do not appear in the WA Monitor dashboard.

**Root cause in code**: The app sets the WAHA webhook per-session (in `onboard.js` → `setWebhook`). This requires `APP_URL` to be set correctly at the time of onboarding. If `APP_URL` was wrong or missing, the webhook URL stored in WAHA is `undefined/webhooks/waha` — silently broken with no startup error.

**Diagnostic**:
```bash
# Check that WAHA webhook is configured (should return the hook URL in its settings)
curl -s \
  -H "X-Api-Key: WAHA_API_KEY" \
  "https://WAHA_PUBLIC_URL/api/settings"
```
Look for `webhooks` or `hookUrl` in the response. It should contain your app URL.

**Fix**:
1. Railway → **WAHA service** (not Node.js service) → Variables
2. Confirm `WHATSAPP_HOOK_URL` is set to exactly: `https://YOUR_APP_URL/webhooks/waha` (no trailing slash)
3. Confirm `WHATSAPP_HOOK_EVENTS` is set to: `message,session.status`
4. **Also check**: Railway → Node.js service → Variables → `APP_URL` must be the correct app URL with no trailing slash
5. If any variable was missing or wrong → fix it → WAHA restarts automatically → wait 30 seconds
6. The CSM must **re-onboard** (scan QR again) to re-register the webhook for their session. Existing sessions with a broken webhook will not start receiving messages until re-onboarded.
7. Test: send a message to the monitored group and check Railway → Node.js → Logs for `"Message saved"`

---

## REPLIES_NOT_MARKING_ANSWERED

**Symptoms**: CSM replied on WhatsApp but the message still shows as "pending" in the dashboard. SLA alerts keep firing for messages that were already answered.

**Root cause in code**: `webhook.js` only marks a message answered when the CSM uses WhatsApp's **Reply** feature (`msg.quotedMsgId`). A standalone message typed into the group — even if it answers the question — does NOT mark anything as answered. This is by design: the app needs to know *which* message was answered.

**Fix**: There is no code change needed — this is expected behaviour. The CSM must use WhatsApp's built-in **Reply** feature:
1. Long-press the customer's message in the WhatsApp group
2. Tap "Reply"
3. Type their response and send

This links the reply to the original message and the dashboard will update to "answered".

**Action**: Educate CSMs on this requirement. Include it in their onboarding instructions.

---

## SLACK_ALERTS_NOT_FIRING

**Symptoms**: Messages appear in the dashboard but no Slack DMs arrive for urgent messages or SLA breaches.

**Diagnostic**:
```bash
RESULT=$(curl -s -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer SLACK_BOT_TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('ok') else d.get('error'))")
echo $RESULT
```

**Fix**:
1. If output is `not_authed` or `invalid_auth`:
   - Slack token is wrong or missing. Check Railway → Node.js → Variables → `SLACK_BOT_TOKEN` starts with `xoxb-`
   - Re-copy from: Slack app → OAuth & Permissions → Bot User OAuth Token
2. If output is `missing_scope`:
   - The `chat:write` scope is missing. Go to Slack app → OAuth & Permissions → Bot Token Scopes → add `chat:write` → reinstall the app
3. If token is valid but still no alerts:
   - Check the CSM's `slack_user_id` is set. Run:
     ```bash
     curl -s \
       -H "apikey: SUPABASE_SERVICE_KEY" \
       -H "Authorization: Bearer SUPABASE_SERVICE_KEY" \
       "SUPABASE_URL/rest/v1/csms?select=name,slack_user_id"
     ```
   - Any null `slack_user_id` = no alerts for that CSM. Use the add-csm skill to link their Slack.
4. For urgent/escalation alerts specifically: check that the message was classified as high/critical urgency or escalation intent. The keyword classifier is strict — only specific keywords trigger immediate alerts (see classifier in `src/classifier/keyword.js`).

---

## SUPABASE_AUTH_FAILURE

**Symptoms**: App shows database errors, Railway logs show "Invalid API key" or "JWT expired", or 401/403 errors when checking data.

**Diagnostic**:
```bash
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "apikey: SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer SUPABASE_SERVICE_KEY" \
  "SUPABASE_URL/rest/v1/csms?select=id&limit=1")
echo $HTTP
```

**Fix**:
1. If HTTP is 401 → wrong key. Go to Supabase → Settings → API → copy the **service_role** key (the longer one, NOT the anon key)
2. Update `SUPABASE_SERVICE_KEY` in Railway → Node.js → Variables
3. Re-run diagnostic to confirm 200

**Important**: Do not confuse the `anon` key (short) with the `service_role` key (longer). The app requires the service_role key to write to the database.

---

## SESSION_NOT_PERSISTING

**Symptoms**: WhatsApp session works but disconnects every time the app restarts or redeploys. Must re-scan QR after every update.

**Root cause**: The WAHA NOWEB engine stores session data on disk. Railway containers are ephemeral — disk data is lost on restart unless a persistent volume is attached.

**Fix**:
1. Railway → WAHA service → click "Add Volume"
2. Mount path: `/app/.waha`
3. Volume name: `waha-sessions`
4. Save → Railway redeploys WAHA
5. After the next QR scan, the session data will be saved to the persistent volume and survive restarts

---

## APP_CRASH_ON_STARTUP

**Symptoms**: Railway shows "Deploy failed" (red), or the service keeps restarting in a crash loop.

**Diagnostic**: Railway → Node.js service → Deployments → click the failed deployment → "View Logs"

Look for the first red error line — it usually says which variable is missing or what crashed.

**Common causes and fixes**:

1. **Missing environment variable** — The app checks for 5 required vars at startup and exits immediately with `[FATAL] Missing env vars: ...` if any are absent. Required: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `WAHA_BASE_URL`, `WAHA_API_KEY`, `SLACK_BOT_TOKEN`. Note: `APP_URL` is NOT in this check — the app will start without it but webhooks will silently break.

2. **Database schema not run** — error like `relation "csms" does not exist`
   - Fix: Go to Supabase → SQL Editor → run the full schema SQL from setup-wizard/references/schema.sql

3. **Wrong WAHA_BASE_URL** — error connecting to WAHA on startup
   - Fix: Set `WAHA_BASE_URL` to exactly `http://waha.railway.internal:3000`

---

## SLA_ALERTS_NOT_FIRING

**Symptoms**: Messages have been unanswered past the SLA deadline but no Slack DM was sent.

**Key fact**: SLA deadline is hardcoded at **1 hour** from when the message was received (`db/supabase.js` → `createSLATimer`). This cannot be changed via environment variable — it requires a code change.

**Diagnostic**:
```bash
# Check for past-due timers with no alert sent
curl -s \
  -H "apikey: SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer SUPABASE_SERVICE_KEY" \
  "SUPABASE_URL/rest/v1/sla_timers?breach_alerted=eq.false&sla_deadline=lt.$(date -u +%Y-%m-%dT%H:%M:%SZ)&select=message_id,sla_deadline&limit=5"
```

If rows are returned with `sla_deadline` values in the past, the SLA checker is not processing them.

**Fix**:
1. Check Railway → Node.js service → Logs and search for `"SLA checker running"` — should appear at startup
2. If missing → the cron job failed to start. Restart the service: Railway → Node.js → "Restart"
3. The SLA checker runs every 5 minutes. Wait up to 5 minutes after restart for the next run.
4. Also verify Slack alerts are working (see SLACK_ALERTS_NOT_FIRING pattern)
5. Verify the CSM's `slack_user_id` is set (null = no DM sent, no error logged)

---

## GROUPS_NOT_SHOWING_IN_ONBOARDING

**Symptoms**: After scanning QR and connecting WhatsApp, the group selection list is empty or missing some groups.

**Root cause in code**: `waha/client.js` → `getGroups` fetches a maximum of **200 chats** and only shows groups (JID ending in `@g.us`). A CSM with more than 200 total WhatsApp chats (groups + individual contacts) may not see all their groups.

**Fix**: This requires a code change to increase the `limit` parameter or implement pagination. As a workaround, the CSM can archive old individual chats in WhatsApp to move groups closer to the top of the list, but this is impractical for many users.

**Code location to fix**: `src/waha/client.js` → `getGroups` → change `limit: 200` to `limit: 500` or implement pagination with multiple API calls.

---

## GROUPS_LOAD_FAILED

**Symptoms**: The "+ Add Group" button on the dashboard is clicked but the modal shows an error ("Could not load groups"), or the modal loads but the group list is empty when it shouldn't be.

**Root cause**: The group loading modal calls `GET /api/dashboard/:csmId/groups/available`, which fetches live groups from WAHA. This fails if: (a) the CSM's WhatsApp session is disconnected, (b) WAHA is down, or (c) the new dashboard routes are not deployed.

**Diagnostic**:
```bash
# Check that the route exists (replace APP_URL and CSM_ID)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "APP_URL/api/dashboard/CSM_ID/groups/available")
echo "Route status: $HTTP"
```

- **200** → route works. The CSM's WAHA session may be disconnected — check WhatsApp status badge on the dashboard. If disconnected, guide them to reconnect (open reconnect URL, scan QR).
- **404** → the new dashboard routes are not deployed. The latest code update hasn't been pushed/deployed yet. Guide the user to push the latest code and redeploy on Railway.
- **500** → WAHA is not responding or the session is in a bad state. Check Railway → Node.js → Logs for the specific error.

**Fix for 404 (routes not deployed)**:
- Use the deploy-update skill to push the latest code
- After redeploy, the route should respond with 200

**Fix for 500 (WAHA session issue)**:
- Ask the CSM to reconnect WhatsApp: open `APP_URL/reconnect/CSM_ID` in their browser and scan the QR code
- Once reconnected, try "+ Add Group" again

---

## ROLE_NOT_SAVED

**Symptoms**: After completing onboarding, the role shows as `csm` even when "Team Lead / Manager" was selected, or the reportees list is empty.

**Root cause**: The `role` and `reportees` columns may not exist in the database (migration not run), or the `complete` API call failed silently because the frontend did not show an error.

**Diagnostic**:
```bash
# Check if the columns exist
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "apikey: SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer SUPABASE_SERVICE_KEY" \
  "SUPABASE_URL/rest/v1/csms?select=role,reportees&limit=0")
echo "Column check: $HTTP"

# If 200, check the actual values for the CSM
curl -s \
  -H "apikey: SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer SUPABASE_SERVICE_KEY" \
  "SUPABASE_URL/rest/v1/csms?select=name,role,reportees&order=created_at.desc&limit=3"
```

**Fix if HTTP = 400** (columns don't exist — migration not run):
1. Go to Supabase → SQL Editor → New query → paste and run:
   ```sql
   ALTER TABLE csms
     ADD COLUMN IF NOT EXISTS role      TEXT NOT NULL DEFAULT 'csm',
     ADD COLUMN IF NOT EXISTS reportees JSONB NOT NULL DEFAULT '[]'::jsonb;
   ```
2. The CSM will need to re-complete the Alert Settings step (Step 4) in their onboarding — their WhatsApp connection does not need to be re-done, only the final step

**Fix if columns exist but values are wrong**:
- Use the add-csm skill to manually set the correct role and reportees for the CSM

---

## CSM_CANT_ONBOARD — EMAIL_ALREADY_EXISTS

**Symptoms**: A CSM tries to onboard at the app URL and sees an error on the first screen after entering their name/email/phone. Railway logs show something like `createCSM: duplicate key value violates unique constraint "csms_email_key"`.

**Root cause**: An admin already added this CSM's email to the database (e.g., via Supabase directly). The onboard route tries to INSERT a new record, which fails on the UNIQUE constraint on `email`.

**Fix**:
1. In Supabase → Table Editor → `csms` table → find the row with that email → delete it
2. The CSM can then complete onboarding normally
3. After onboarding, use the **add-csm** skill to add their Slack details

**Prevention**: Never manually insert records into the `csms` table. Always let CSMs self-register via the app URL.

---

## APP_URL_TRAILING_SLASH

**Symptoms**: Messages not arriving despite WAHA being connected, or reconnect links in Slack DMs are broken (404 when clicked).

**Root cause**: If `APP_URL` was set with a trailing slash (e.g., `https://app.railway.app/`), the webhook URL becomes `https://app.railway.app//webhooks/waha` (double slash). Some servers reject this; WAHA may silently fail to deliver.

**Fix**: Railway → Node.js service → Variables → update `APP_URL` to remove the trailing slash. Example: change `https://app.railway.app/` to `https://app.railway.app`.

Railway will redeploy automatically. The CSM does not need to re-scan — just send a test message to verify delivery.
