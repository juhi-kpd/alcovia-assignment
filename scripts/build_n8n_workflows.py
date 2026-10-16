"""Write the n8n workflow exports in n8n/ (import each file in n8n: Workflows → Import from file).

Kept as code so every workflow shares the same credential names and so the SQL inside the
Postgres nodes can be checked against db/schema.sql (see scripts/check_n8n_sql.py).
Credentials referenced (create them in n8n with these names): "Alcovia Postgres", "Meta Marketing API",
"ClickUp", "Smallest.ai", "WhatsApp Cloud API", "Razorpay webhook secret" (env var RAZORPAY_WEBHOOK_SECRET).
"""
import json, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "n8n"
OUT.mkdir(exist_ok=True)
NS = uuid.UUID("6f1c2b1e-5a2d-4c1e-9a77-0a1c0b1a2026")

PG = {"postgres": {"id": "alcovia-postgres", "name": "Alcovia Postgres"}}
HDR = lambda cid, name: {"httpHeaderAuth": {"id": cid, "name": name}}

def node(wf, name, ntype, version, params, x, y, creds=None, notes=None):
    n = {"parameters": params, "id": str(uuid.uuid5(NS, wf + name)), "name": name, "type": ntype, "typeVersion": version, "position": [x, y]}
    if creds: n["credentials"] = creds
    if notes: n["notes"], n["notesInFlow"] = notes, True
    return n

def schedule(wf, cron, x=0, y=0):
    return node(wf, "Schedule", "n8n-nodes-base.scheduleTrigger", 1.2,
                {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}}, x, y)

def pg(wf, name, query, params_expr, x, y, notes=None):
    p = {"operation": "executeQuery", "query": query, "options": {}}
    if params_expr:
        # array form, so values that contain commas (campaign names, alert lines) are passed intact
        parts = params_expr[1:].split("}},{{")
        parts = [x.replace("{{", "").replace("}}", "").strip() for x in parts]
        p["options"]["queryReplacement"] = "={{ [" + ", ".join(parts) + "] }}"
    return node(wf, name, "n8n-nodes-base.postgres", 2.5, p, x, y, PG, notes)

def code(wf, name, js, x, y, notes=None):
    return node(wf, name, "n8n-nodes-base.code", 2, {"jsCode": js}, x, y, notes=notes)

def http(wf, name, method, url, x, y, creds=None, query=None, body=None, notes=None):
    p = {"method": method, "url": url, "options": {}}
    if creds:
        p["authentication"] = "genericCredentialType"; p["genericAuthType"] = "httpHeaderAuth"
    if query:
        p["sendQuery"] = True; p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in query]}
    if body:
        p["sendBody"] = True; p["specifyBody"] = "json"; p["jsonBody"] = body
    return node(wf, name, "n8n-nodes-base.httpRequest", 4.2, p, x, y, creds, notes)

def write(fname, title, nodes, chain, tags):
    conns = {}
    for a, b in chain:
        conns.setdefault(a, {"main": [[]]})["main"][0].append({"node": b, "type": "main", "index": 0})
    wf = {"name": title, "nodes": nodes, "connections": conns, "active": False,
          "settings": {"executionOrder": "v1", "timezone": "Asia/Kolkata", "saveManualExecutions": True},
          "pinData": {}, "meta": {"templateCredsSetupCompleted": False},
          "tags": [{"name": t} for t in tags]}
    (OUT / fname).write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n")

# ------------------------------------------------------------------ 01 Razorpay → payments, invoices
wf = "01"
write("01_razorpay_payments.json", "01 · Razorpay → payments and invoices", [
    node(wf, "Razorpay webhook", "n8n-nodes-base.webhook", 2,
         {"httpMethod": "POST", "path": "razorpay", "responseMode": "onReceived", "options": {"rawBody": True}}, 0, 0,
         notes="Razorpay Dashboard → Webhooks → events payment.captured and invoice.paid"),
    code(wf, "Verify signature and map", r"""
// Razorpay signs the raw body with the webhook secret (HMAC-SHA256, header x-razorpay-signature).
// Needs NODE_FUNCTION_ALLOW_BUILTIN=crypto on the n8n instance.
const crypto = require('crypto');
const out = [];
for (const item of $input.all()) {
  const raw = item.binary?.data ? Buffer.from(item.binary.data.data, 'base64').toString() : JSON.stringify(item.json.body);
  const sig = crypto.createHmac('sha256', $env.RAZORPAY_WEBHOOK_SECRET).update(raw).digest('hex');
  if (sig !== item.json.headers['x-razorpay-signature']) throw new Error('Bad Razorpay signature');
  const ev = item.json.body;
  if (ev.event === 'payment.captured') {
    const p = ev.payload.payment.entity, notes = p.notes || {};
    out.push({ json: {
      payment_id: p.id,
      product: notes.product,                       // 'trial' | 'full' | 'workshop', set on the payment link
      invoice_id: p.invoice_id || '',
      workshop_id: notes.workshop_id || '',
      student_id: notes.student_id || '',
      utm_creative_id: notes.utm_content || '',     // Meta ad id carried from the ad's UTM
      amount_inr: p.amount / 100,
      paid_at: new Date(p.created_at * 1000).toISOString(),
    }});
  } else if (ev.event === 'invoice.paid') {
    const inv = ev.payload.invoice.entity;
    out.push({ json: { payment_id: inv.payment_id, product: inv.notes?.product || 'full', invoice_id: inv.id,
      workshop_id: '', student_id: inv.notes?.student_id || '', utm_creative_id: '',
      amount_inr: inv.amount_paid / 100, paid_at: new Date(inv.paid_at * 1000).toISOString() }});
  }
}
return out;
""".strip(), 260, 0),
    pg(wf, "Insert payment", """INSERT INTO alcovia.payments (payment_id, product, invoice_id, workshop_id, student_id, utm_creative_id, amount_inr, paid_at)
VALUES ($1, $2, nullif($3, ''), nullif($4, ''), nullif($5, ''), nullif($6, ''), $7::numeric, $8::timestamptz)
ON CONFLICT (payment_id) DO NOTHING""",
       "={{ $json.payment_id }},{{ $json.product }},{{ $json.invoice_id }},{{ $json.workshop_id }},{{ $json.student_id }},{{ $json.utm_creative_id }},{{ $json.amount_inr }},{{ $json.paid_at }}", 520, 0),
    pg(wf, "Mark invoice paid", """UPDATE alcovia.invoices SET paid_on = ($2::timestamptz AT TIME ZONE 'Asia/Kolkata')::date
WHERE invoice_id = $1 AND paid_on IS NULL""",
       "={{ $('Verify signature and map').item.json.invoice_id }},{{ $('Verify signature and map').item.json.paid_at }}", 780, 0),
], [("Razorpay webhook", "Verify signature and map"), ("Verify signature and map", "Insert payment"), ("Insert payment", "Mark invoice paid")],
   ["gtm", "revenue"])

# ------------------------------------------------------------------ 02 Meta Ads → ad_daily
wf = "02"
write("02_meta_ads_daily.json", "02 · Meta Ads insights → ad_daily (daily 06:00)", [
    schedule(wf, "0 6 * * *"),
    http(wf, "Get yesterday's ad insights", "GET", "=https://graph.facebook.com/v21.0/act_{{ $env.META_AD_ACCOUNT_ID }}/insights", 240, 0,
         HDR("meta-api", "Meta Marketing API"),
         query=[("level", "ad"), ("date_preset", "yesterday"), ("time_increment", "1"), ("limit", "500"),
                ("fields", "ad_id,ad_name,campaign_id,campaign_name,spend,impressions,reach,inline_link_clicks,date_start")],
         notes="Header auth: Authorization: Bearer <system user token> with ads_read"),
    code(wf, "Flatten rows", r"""
// One output item per ad. Campaign objective comes from the naming convention "Program · …" / "Workshop · …".
return $input.first().json.data.map(r => ({ json: {
  campaign_id: r.campaign_id,
  campaign_name: r.campaign_name,
  objective: /^workshop/i.test(r.campaign_name) ? 'workshop' : 'program',
  creative_id: r.ad_id,
  creative_name: r.ad_name,
  day: r.date_start,
  spend_inr: Number(r.spend || 0),
  impressions: Number(r.impressions || 0),
  reach: Number(r.reach || 0),
  link_clicks: Number(r.inline_link_clicks || 0),
}}));
""".strip(), 480, 0),
    pg(wf, "Upsert campaign", """INSERT INTO alcovia.campaigns (campaign_id, name, objective) VALUES ($1, $2, $3)
ON CONFLICT (campaign_id) DO UPDATE SET name = EXCLUDED.name""",
       "={{ $json.campaign_id }},{{ $json.campaign_name }},{{ $json.objective }}", 720, 0),
    pg(wf, "Upsert creative", """INSERT INTO alcovia.creatives (creative_id, campaign_id, name, format, landing_page)
VALUES ($1, $2, $3, 'static', '/career-program')
ON CONFLICT (creative_id) DO UPDATE SET name = EXCLUDED.name""",
       "={{ $('Flatten rows').item.json.creative_id }},{{ $('Flatten rows').item.json.campaign_id }},{{ $('Flatten rows').item.json.creative_name }}", 960, 0,
       notes="Format and landing page default here; correct them once per new ad in the creatives table"),
    pg(wf, "Upsert ad_daily", """INSERT INTO alcovia.ad_daily (creative_id, day, spend_inr, impressions, reach, link_clicks)
VALUES ($1, $2::date, $3::numeric, $4::int, $5::int, $6::int)
ON CONFLICT (creative_id, day) DO UPDATE
SET spend_inr = EXCLUDED.spend_inr, impressions = EXCLUDED.impressions, reach = EXCLUDED.reach, link_clicks = EXCLUDED.link_clicks""",
       "={{ $('Flatten rows').item.json.creative_id }},{{ $('Flatten rows').item.json.day }},{{ $('Flatten rows').item.json.spend_inr }},{{ $('Flatten rows').item.json.impressions }},{{ $('Flatten rows').item.json.reach }},{{ $('Flatten rows').item.json.link_clicks }}", 1200, 0),
], [("Schedule", "Get yesterday's ad insights"), ("Get yesterday's ad insights", "Flatten rows"), ("Flatten rows", "Upsert campaign"),
    ("Upsert campaign", "Upsert creative"), ("Upsert creative", "Upsert ad_daily")], ["gtm", "campaigns"])

# ------------------------------------------------------------------ 03 ClickUp → lead stages
wf = "03"
write("03_clickup_lead_stages.json", "03 · ClickUp lead status → funnel timestamps", [
    node(wf, "ClickUp status changed", "n8n-nodes-base.clickUpTrigger", 1,
         {"team": "={{ $env.CLICKUP_TEAM_ID }}", "events": ["taskCreated", "taskStatusUpdated"], "filters": {}}, 0, 0,
         {"clickUpApi": {"id": "clickup", "name": "ClickUp"}}, "Only tasks in the Leads list are processed"),
    http(wf, "Get task", "GET", "=https://api.clickup.com/api/v2/task/{{ $json.task_id }}", 240, 0, HDR("clickup-http", "ClickUp")),
    code(wf, "Map status to stage", r"""
// ClickUp statuses in the Leads list, in funnel order. Must match exactly (set up by the process designer).
const STAGE = {
  'new lead': 'lead', 'qualified': 'qualified', 'discovery call set': 'discovery_set',
  'discovery call done': 'discovery_showed', 'ambition interview done': 'ambition_done',
  'architect session done': 'architect_done', 'paid': 'paid', 'lost': 'dropped',
};
const t = $input.first().json;
if (t.list?.id !== $env.CLICKUP_LEADS_LIST_ID) return [];
const field = name => (t.custom_fields || []).find(f => f.name === name)?.value ?? '';
const history = $('ClickUp status changed').first().json.history_items?.[0];
const before = history?.before?.status?.toLowerCase();
return [{ json: {
  lead_id: t.id,
  source: field('Source') === 'Organic' ? 'organic' : 'meta',
  creative_id: field('Meta ad id'),
  parent_name: field('Parent name'), parent_phone: field('Parent phone'), teen_name: field('Teen name'),
  stage: STAGE[t.status.status.toLowerCase()] || 'lead',
  drop_stage: STAGE[before] && STAGE[before] !== 'dropped' && STAGE[before] !== 'paid' ? STAGE[before] : 'lead',
  discovery_call_at: field('Discovery call time') ? new Date(Number(field('Discovery call time'))).toISOString() : '',
}}];
""".strip(), 480, 0),
    pg(wf, "Upsert lead stage", """INSERT INTO alcovia.leads (lead_id, source, creative_id, parent_name, parent_phone, teen_name, created_at)
VALUES ($1, $2, nullif($3, ''), nullif($4, ''), nullif($5, ''), nullif($6, ''), now())
ON CONFLICT (lead_id) DO UPDATE SET
  qualified_at        = CASE WHEN $7 = 'qualified'        THEN coalesce(leads.qualified_at, now())        ELSE leads.qualified_at END,
  discovery_set_at    = CASE WHEN $7 = 'discovery_set'    THEN coalesce(leads.discovery_set_at, now())    ELSE leads.discovery_set_at END,
  discovery_call_at   = coalesce(nullif($9, '')::timestamptz, leads.discovery_call_at),
  discovery_showed_at = CASE WHEN $7 = 'discovery_showed' THEN coalesce(leads.discovery_showed_at, now()) ELSE leads.discovery_showed_at END,
  ambition_done_at    = CASE WHEN $7 = 'ambition_done'    THEN coalesce(leads.ambition_done_at, now())    ELSE leads.ambition_done_at END,
  architect_done_at   = CASE WHEN $7 = 'architect_done'   THEN coalesce(leads.architect_done_at, now())   ELSE leads.architect_done_at END,
  paid_at             = CASE WHEN $7 = 'paid'             THEN coalesce(leads.paid_at, now())             ELSE leads.paid_at END,
  dropped_at          = CASE WHEN $7 = 'dropped'          THEN coalesce(leads.dropped_at, now())          ELSE leads.dropped_at END,
  drop_stage          = CASE WHEN $7 = 'dropped'          THEN $8                                         ELSE leads.drop_stage END""",
       "={{ $json.lead_id }},{{ $json.source }},{{ $json.creative_id }},{{ $json.parent_name }},{{ $json.parent_phone }},{{ $json.teen_name }},{{ $json.stage }},{{ $json.drop_stage }},{{ $json.discovery_call_at }}", 720, 0),
], [("ClickUp status changed", "Get task"), ("Get task", "Map status to stage"), ("Map status to stage", "Upsert lead stage")], ["gtm", "funnel"])

# ------------------------------------------------------------------ 04 Smallest.ai reminder and renewal calls
wf = "04"
write("04_smallest_ai_calls.json", "04 · Smallest.ai reminder and renewal calls (every 15 min)", [
    schedule(wf, "*/15 9-20 * * *"),
    pg(wf, "Calls due now", """-- Discovery call reminders 24 h and 1 h before, and renewal calls 14 days before a trial ends.
SELECT 'discovery_reminder_24h' AS kind, l.lead_id AS ref_id, l.parent_phone AS phone, l.parent_name AS name,
       to_char(l.discovery_call_at AT TIME ZONE 'Asia/Kolkata', 'Dy DD Mon, HH12:MI AM') AS when_text
FROM alcovia.leads l
WHERE l.discovery_call_at BETWEEN now() + interval '23 hours 45 minutes' AND now() + interval '24 hours'
  AND l.discovery_showed_at IS NULL AND l.dropped_at IS NULL AND l.parent_phone IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM alcovia.outreach_log o WHERE o.kind = 'discovery_reminder_24h' AND o.ref_id = l.lead_id)
UNION ALL
SELECT 'discovery_reminder_1h', l.lead_id, l.parent_phone, l.parent_name,
       to_char(l.discovery_call_at AT TIME ZONE 'Asia/Kolkata', 'HH12:MI AM')
FROM alcovia.leads l
WHERE l.discovery_call_at BETWEEN now() + interval '45 minutes' AND now() + interval '60 minutes'
  AND l.discovery_showed_at IS NULL AND l.dropped_at IS NULL AND l.parent_phone IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM alcovia.outreach_log o WHERE o.kind = 'discovery_reminder_1h' AND o.ref_id = l.lead_id)
UNION ALL
SELECT 'renewal_call', e.enrolment_id, s.parent_phone, s.name, to_char(e.end_on, 'DD Mon')
FROM alcovia.enrolments e JOIN alcovia.students s USING (student_id)
WHERE e.plan = 'trial' AND NOT e.renewed AND e.end_on = current_date + 14 AND s.parent_phone IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM alcovia.outreach_log o WHERE o.kind = 'renewal_call' AND o.ref_id = e.enrolment_id)""", None, 240, 0),
    http(wf, "Place call", "POST", "={{ $env.SMALLEST_OUTBOUND_URL }}", 480, 0, HDR("smallest", "Smallest.ai"),
         body="={{ JSON.stringify({ agentId: $json.kind === 'renewal_call' ? $env.SMALLEST_RENEWAL_AGENT_ID : $env.SMALLEST_REMINDER_AGENT_ID, phoneNumber: $json.phone, variables: { name: $json.name, when: $json.when_text } }) }}",
         notes="Outbound-call endpoint and agent ids from the Smallest.ai Atoms dashboard (set as env vars)"),
    pg(wf, "Log call", """INSERT INTO alcovia.outreach_log (kind, ref_id, channel, provider_ref) VALUES ($1, $2, 'smallest_ai', nullif($3, ''))""",
       "={{ $('Calls due now').item.json.kind }},{{ $('Calls due now').item.json.ref_id }},{{ $json.id ?? '' }}", 720, 0),
], [("Schedule", "Calls due now"), ("Calls due now", "Place call"), ("Place call", "Log call")], ["gtm", "funnel", "renewals"])

# ------------------------------------------------------------------ 05 nightly alerts to advisors
wf = "05"
write("05_nightly_advisor_alerts.json", "05 · Raise student alerts and message advisors (daily 21:30)", [
    schedule(wf, "30 21 * * *"),
    pg(wf, "Raise new alerts", """WITH overdue AS (
  SELECT student_id, 'task_overdue' AS kind, count(*) || ' tasks more than 3 days overdue' AS detail
  FROM alcovia.tasks WHERE done_on IS NULL AND due_on < current_date - 3 GROUP BY student_id
), behind AS (
  SELECT sb.student_id, 'subject_behind' AS kind,
         sb.name || ' ' || round(100.0 * count(DISTINCT cs.chapter_id) / sb.chapters_total) || '% done vs '
           || round(100.0 * (current_date - date '2026-04-01') / 365) || '% expected' AS detail
  FROM alcovia.subjects sb JOIN alcovia.chapters c USING (subject_id)
  LEFT JOIN alcovia.chapter_stages cs ON cs.chapter_id = c.chapter_id AND cs.stage = 1
  GROUP BY sb.student_id, sb.name, sb.chapters_total
  HAVING 100.0 * (current_date - date '2026-04-01') / 365 - 100.0 * count(DISTINCT cs.chapter_id) / sb.chapters_total > 15
), inactive AS (
  SELECT s.student_id, 'inactive' AS kind, 'No app activity for ' || (current_date - max(u.day)) || ' days' AS detail
  FROM alcovia.students s LEFT JOIN alcovia.app_usage_daily u USING (student_id)
  GROUP BY s.student_id HAVING coalesce(current_date - max(u.day), 99) >= 7
), candidates AS (SELECT * FROM overdue UNION ALL SELECT * FROM behind UNION ALL SELECT * FROM inactive)
INSERT INTO alcovia.alerts (student_id, kind, detail, raised_at)
SELECT c.student_id, c.kind, c.detail, now() FROM candidates c
WHERE NOT EXISTS (SELECT 1 FROM alcovia.alerts a WHERE a.student_id = c.student_id AND a.kind = c.kind
                  AND a.actioned_at IS NULL AND (a.kind <> 'subject_behind' OR a.detail LIKE split_part(c.detail, ' ', 1) || ' %'))
RETURNING student_id, kind, detail""", None, 240, 0, "Skips an alert that is already open for the same student and kind"),
    pg(wf, "Open alerts by advisor", """SELECT ad.advisor_id, ad.name AS advisor, ad.phone,
       string_agg(s.name || ': ' || a.detail, E'\\n' ORDER BY s.name) AS lines, count(*) AS n
FROM alcovia.alerts a JOIN alcovia.students s USING (student_id) JOIN alcovia.advisors ad USING (advisor_id)
WHERE a.actioned_at IS NULL AND ad.phone IS NOT NULL
GROUP BY ad.advisor_id, ad.name, ad.phone""", None, 480, 0),
    http(wf, "WhatsApp advisor", "POST", "=https://graph.facebook.com/v21.0/{{ $env.WHATSAPP_PHONE_NUMBER_ID }}/messages", 720, 0,
         HDR("whatsapp", "WhatsApp Cloud API"),
         body="={{ JSON.stringify({ messaging_product: 'whatsapp', to: $json.phone, type: 'template', template: { name: 'advisor_daily_alerts', language: { code: 'en' }, components: [{ type: 'body', parameters: [{ type: 'text', text: $json.advisor }, { type: 'text', text: String($json.n) }, { type: 'text', text: $json.lines.slice(0, 900) }] }] } }) }}",
         notes="Template 'advisor_daily_alerts' must be approved in WhatsApp Manager"),
    pg(wf, "Log message", """INSERT INTO alcovia.outreach_log (kind, ref_id, channel, provider_ref) VALUES ('advisor_alert', $1, 'whatsapp', nullif($2, ''))""",
       "={{ $('Open alerts by advisor').item.json.advisor_id }},{{ $json.messages?.[0]?.id ?? '' }}", 960, 0),
], [("Schedule", "Raise new alerts"), ("Raise new alerts", "Open alerts by advisor"), ("Open alerts by advisor", "WhatsApp advisor"), ("WhatsApp advisor", "Log message")],
   ["students", "alerts"])
# n8n runs the next node once per input item; the advisor query should run once, so mark it executeOnce.
wfj = json.loads((OUT / "05_nightly_advisor_alerts.json").read_text())
for n in wfj["nodes"]:
    if n["name"] == "Open alerts by advisor": n["executeOnce"] = True
(OUT / "05_nightly_advisor_alerts.json").write_text(json.dumps(wfj, indent=2, ensure_ascii=False) + "\n")

# ------------------------------------------------------------------ 06 weekly parent summary
wf = "06"
write("06_weekly_parent_summary.json", "06 · Weekly parent summary on WhatsApp (Sunday 18:00)", [
    schedule(wf, "0 18 * * 0"),
    pg(wf, "Week per student", """SELECT s.student_id, s.name, s.parent_phone,
  coalesce((SELECT sum(actual_min) FROM alcovia.focus_sessions f WHERE f.student_id = s.student_id AND f.started_at > now() - interval '7 days'), 0) AS focus_min,
  (SELECT round(avg(correct) * 10) FROM alcovia.quiz_attempts q WHERE q.student_id = s.student_id AND q.quiz_date > current_date - 7) AS quiz_pct,
  (SELECT count(*) FROM alcovia.chapter_stages cs JOIN alcovia.chapters c USING (chapter_id) JOIN alcovia.subjects sb USING (subject_id)
    WHERE sb.student_id = s.student_id AND cs.reached_on > current_date - 7) AS chapter_steps,
  (SELECT count(*) FILTER (WHERE p.attended) || ' of ' || count(*) FROM alcovia.activity_participants p JOIN alcovia.activities a USING (activity_id)
    WHERE p.student_id = s.student_id AND a.held AND a.scheduled_on > current_date - 7) AS sessions
FROM alcovia.students s
WHERE s.parent_phone IS NOT NULL""", None, 240, 0),
    code(wf, "Write message", r"""
// Three numbers and one line, so a parent can read it in ten seconds.
return $input.all().map(({ json: s }) => ({ json: { ...s, text:
  `${s.name.split(' ')[0]}'s week: ${s.focus_min} focus minutes, ${s.chapter_steps} chapter steps completed, ` +
  `${s.sessions} sessions attended` + (s.quiz_pct != null ? `, quiz average ${s.quiz_pct}%.` : '.') }}));
""".strip(), 480, 0),
    http(wf, "WhatsApp parent", "POST", "=https://graph.facebook.com/v21.0/{{ $env.WHATSAPP_PHONE_NUMBER_ID }}/messages", 720, 0,
         HDR("whatsapp", "WhatsApp Cloud API"),
         body="={{ JSON.stringify({ messaging_product: 'whatsapp', to: $json.parent_phone, type: 'template', template: { name: 'parent_weekly_summary', language: { code: 'en' }, components: [{ type: 'body', parameters: [{ type: 'text', text: $json.text }] }] } }) }}"),
    pg(wf, "Log message", """INSERT INTO alcovia.outreach_log (kind, ref_id, channel, provider_ref) VALUES ('parent_summary', $1, 'whatsapp', nullif($2, ''))""",
       "={{ $('Write message').item.json.student_id }},{{ $json.messages?.[0]?.id ?? '' }}", 960, 0),
], [("Schedule", "Week per student"), ("Week per student", "Write message"), ("Write message", "WhatsApp parent"), ("WhatsApp parent", "Log message")],
   ["students", "parents"])

# ------------------------------------------------------------------ 07 WHOOP sync
wf = "07"
write("07_whoop_daily_sync.json", "07 · WHOOP recovery and sleep → wearable_daily (daily 07:00)", [
    schedule(wf, "0 7 * * *"),
    pg(wf, "Connected students", """SELECT student_id, access_token FROM alcovia.wearable_tokens WHERE provider = 'whoop' AND expires_at > now()""",
       None, 240, 0, "Token refresh runs in a separate small workflow; expired tokens are skipped"),
    http(wf, "Get recovery", "GET", "https://api.prod.whoop.com/developer/v2/recovery", 480, -80,
         query=[("start", "={{ $now.minus({ days: 1 }).startOf('day').toISO() }}"), ("limit", "1")],
         notes="Authorization: Bearer {{ access_token }} (set as header below)"),
    http(wf, "Get sleep", "GET", "https://api.prod.whoop.com/developer/v2/activity/sleep", 720, -80,
         query=[("start", "={{ $now.minus({ days: 1 }).startOf('day').toISO() }}"), ("limit", "1")]),
    code(wf, "Shape row", r"""
// Pair each student's recovery and sleep responses (same item order as 'Connected students').
const students = $('Connected students').all(), rec = $('Get recovery').all(), sleep = $('Get sleep').all();
return students.map((s, i) => {
  const r = rec[i]?.json.records?.[0]?.score, sl = sleep[i]?.json.records?.[0]?.score?.stage_summary;
  const asleepMs = sl ? sl.total_in_bed_time_milli - sl.total_awake_time_milli : null;
  return { json: { student_id: s.json.student_id, day: $now.minus({ days: 1 }).toISODate(),
    recovery_pct: r?.recovery_score ?? '', sleep_hours: asleepMs ? (asleepMs / 3.6e6).toFixed(2) : '' } };
});
""".strip(), 960, -80),
    pg(wf, "Upsert wearable_daily", """INSERT INTO alcovia.wearable_daily (student_id, day, source, sleep_hours, recovery_pct)
VALUES ($1, $2::date, 'whoop', nullif($3, '')::numeric, nullif($4, '')::numeric::int)
ON CONFLICT (student_id, day) DO UPDATE SET sleep_hours = EXCLUDED.sleep_hours, recovery_pct = EXCLUDED.recovery_pct, source = 'whoop'""",
       "={{ $json.student_id }},{{ $json.day }},{{ $json.sleep_hours }},{{ $json.recovery_pct }}", 1200, -80),
], [("Schedule", "Connected students"), ("Connected students", "Get recovery"), ("Get recovery", "Get sleep"), ("Get sleep", "Shape row"), ("Shape row", "Upsert wearable_daily")],
   ["students", "wearables"])
# per-student bearer header on the two WHOOP calls
wfj = json.loads((OUT / "07_whoop_daily_sync.json").read_text())
for n in wfj["nodes"]:
    if n["name"] in ("Get recovery", "Get sleep"):
        n["parameters"]["sendHeaders"] = True
        n["parameters"]["headerParameters"] = {"parameters": [{"name": "Authorization", "value": "=Bearer {{ $('Connected students').item.json.access_token }}"}]}
    if n["name"] == "Shape row": n["executeOnce"] = True
(OUT / "07_whoop_daily_sync.json").write_text(json.dumps(wfj, indent=2, ensure_ascii=False) + "\n")

# ------------------------------------------------------------------ 08 landing page speed
wf = "08"
write("08_pagespeed_weekly.json", "08 · Landing page mobile load time (Monday 07:00)", [
    schedule(wf, "0 7 * * 1"),
    code(wf, "Pages", "return ['/career-program', '/trial-offer', '/workshop-signup'].map(page => ({ json: { page, url: 'https://alcovia.life' + page } }));", 240, 0,
         notes="Visits and form submits per page come from site analytics into landing_page_daily; this flow adds load time"),
    http(wf, "PageSpeed (mobile)", "GET", "https://www.googleapis.com/pagespeedonline/v5/runPagespeed", 480, 0,
         query=[("url", "={{ $json.url }}"), ("strategy", "mobile"), ("key", "={{ $env.PAGESPEED_API_KEY }}")]),
    pg(wf, "Save load time", """UPDATE alcovia.landing_page_daily SET mobile_load_s = round(($2::numeric / 1000), 2)
WHERE page = $1 AND day >= current_date - 7""",
       "={{ $('Pages').item.json.page }},{{ $json.lighthouseResult.audits['largest-contentful-paint'].numericValue }}", 720, 0),
], [("Schedule", "Pages"), ("Pages", "PageSpeed (mobile)"), ("PageSpeed (mobile)", "Save load time")], ["gtm", "landing-pages"])

print("\n".join(sorted(p.name for p in OUT.glob("*.json"))))
