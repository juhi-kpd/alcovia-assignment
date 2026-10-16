-- Alcovia data model (PostgreSQL 14+)
-- One database behind the GTM tracker, the student tracker and the n8n automations.
-- Sources: Razorpay, Meta Ads, ClickUp, Alcovia app events, wearables, Google Calendar, facilitator forms.

DROP SCHEMA IF EXISTS alcovia CASCADE;
CREATE SCHEMA alcovia;
SET search_path TO alcovia;

------------------------------------------------------------------------
-- GTM: campaigns, leads, money
------------------------------------------------------------------------

CREATE TABLE campaigns (
  campaign_id    text PRIMARY KEY,            -- Meta campaign id
  name           text NOT NULL,
  objective      text NOT NULL CHECK (objective IN ('program','workshop'))
);

CREATE TABLE creatives (
  creative_id    text PRIMARY KEY,            -- Meta ad id
  campaign_id    text NOT NULL REFERENCES campaigns,
  name           text NOT NULL,
  format         text NOT NULL CHECK (format IN ('reel','carousel','static','video')),
  landing_page   text NOT NULL
);

-- One row per creative per day, written by n8n from the Meta Marketing API.
CREATE TABLE ad_daily (
  creative_id    text NOT NULL REFERENCES creatives,
  day            date NOT NULL,
  spend_inr      numeric(12,2) NOT NULL,
  impressions    integer NOT NULL,
  reach          integer NOT NULL,             -- frequency = impressions / reach
  link_clicks    integer NOT NULL,
  PRIMARY KEY (creative_id, day)
);

CREATE TABLE landing_page_daily (
  page           text NOT NULL,
  day            date NOT NULL,
  visits         integer NOT NULL,
  conversions    integer NOT NULL,             -- form submits; drop-off = 1 - conversions/visits
  mobile_load_s  numeric(4,2) NOT NULL,        -- PageSpeed largest contentful paint, mobile
  PRIMARY KEY (page, day)
);

-- One row per lead. Each funnel stage is a timestamp, set by n8n when the ClickUp status changes.
CREATE TABLE leads (
  lead_id              text PRIMARY KEY,       -- ClickUp task id
  source               text NOT NULL CHECK (source IN ('meta','organic')),
  creative_id          text REFERENCES creatives,
  parent_name          text,
  parent_phone         text,                   -- E.164, used for Smallest.ai reminder calls
  teen_name            text,
  discovery_call_at    timestamptz,            -- scheduled time of the discovery call
  created_at           timestamptz NOT NULL,
  qualified_at         timestamptz,
  discovery_set_at     timestamptz,
  discovery_showed_at  timestamptz,
  ambition_done_at     timestamptz,
  architect_done_at    timestamptz,
  paid_at              timestamptz,
  dropped_at           timestamptz,
  drop_stage           text CHECK (drop_stage IN ('lead','qualified','discovery_set','discovery_showed','ambition_done','architect_done'))
);
CREATE INDEX leads_created_idx ON leads (created_at);

CREATE TABLE revenue_targets (
  month          date PRIMARY KEY,             -- first day of month
  target_inr     numeric(12,2) NOT NULL
);

------------------------------------------------------------------------
-- People
------------------------------------------------------------------------

CREATE TABLE advisors (
  advisor_id     text PRIMARY KEY,
  name           text NOT NULL,
  phone          text                          -- WhatsApp number for nightly alerts
);

CREATE TABLE pods (
  pod_id         text PRIMARY KEY,
  name           text NOT NULL
);

CREATE TABLE students (
  student_id     text PRIMARY KEY,
  lead_id        text REFERENCES leads,
  name           text NOT NULL,
  grade          smallint NOT NULL,
  advisor_id     text NOT NULL REFERENCES advisors,
  pod_id         text NOT NULL REFERENCES pods,
  joined_on      date NOT NULL,
  parent_phone   text,                         -- WhatsApp number for the weekly parent summary
  wearable       text CHECK (wearable IN ('apple_health','health_connect','whoop','garmin'))
);

-- Trial (3 months) and full program enrolments; renewals come from end_on.
CREATE TABLE enrolments (
  enrolment_id   text PRIMARY KEY,
  student_id     text NOT NULL REFERENCES students,
  plan           text NOT NULL CHECK (plan IN ('trial','full')),
  start_on       date NOT NULL,
  end_on         date NOT NULL,
  renewed        boolean NOT NULL DEFAULT false
);

------------------------------------------------------------------------
-- Money in (Razorpay)
------------------------------------------------------------------------

CREATE TABLE workshops (
  workshop_id    text PRIMARY KEY,
  title          text NOT NULL,
  held_on        date NOT NULL,
  seat_price_inr numeric(10,2) NOT NULL DEFAULT 3999
);

CREATE TABLE invoices (
  invoice_id     text PRIMARY KEY,             -- Razorpay invoice id
  student_id     text REFERENCES students,
  billed_to      text NOT NULL,
  product        text NOT NULL CHECK (product IN ('trial','full')),
  amount_inr     numeric(12,2) NOT NULL,
  issued_on      date NOT NULL,
  due_on         date NOT NULL,
  paid_on        date
);

CREATE TABLE payments (
  payment_id     text PRIMARY KEY,             -- Razorpay payment id
  product        text NOT NULL CHECK (product IN ('trial','full','workshop')),
  invoice_id     text REFERENCES invoices,
  workshop_id    text REFERENCES workshops,
  student_id     text REFERENCES students,
  utm_creative_id text REFERENCES creatives,   -- ad that drove the payment (from the UTM on the checkout link)
  amount_inr     numeric(12,2) NOT NULL,
  paid_at        timestamptz NOT NULL
);
CREATE INDEX payments_paid_idx ON payments (paid_at);

------------------------------------------------------------------------
-- Student rigour: day level
------------------------------------------------------------------------

CREATE TABLE app_usage_daily (
  student_id     text NOT NULL REFERENCES students,
  day            date NOT NULL,
  active_minutes numeric(6,2) NOT NULL,        -- foreground time from Mixpanel session events
  PRIMARY KEY (student_id, day)
);

CREATE TABLE focus_sessions (
  session_id     bigserial PRIMARY KEY,
  student_id     text NOT NULL REFERENCES students,
  started_at     timestamptz NOT NULL,
  planned_min    smallint NOT NULL,
  actual_min     smallint NOT NULL,
  completed      boolean NOT NULL,
  chapter_id     bigint                         -- set when the session is tied to a chapter
);

CREATE TABLE quizzes (
  quiz_date      date PRIMARY KEY,
  topic          text NOT NULL,
  questions      smallint NOT NULL
);

CREATE TABLE quiz_attempts (
  quiz_date      date NOT NULL REFERENCES quizzes,
  student_id     text NOT NULL REFERENCES students,
  correct        smallint NOT NULL,
  PRIMARY KEY (quiz_date, student_id)
);

CREATE TABLE timetable_slots (
  student_id     text NOT NULL REFERENCES students,
  day            date NOT NULL,
  slot_type      text NOT NULL CHECK (slot_type IN ('self_study','tuition','extracurricular','free')),
  planned_min    smallint NOT NULL,
  done           boolean NOT NULL,
  PRIMARY KEY (student_id, day, slot_type)
);

CREATE TABLE wearable_daily (
  student_id     text NOT NULL REFERENCES students,
  day            date NOT NULL,
  source         text NOT NULL,
  active_min     smallint,
  sleep_hours    numeric(4,2),
  recovery_pct   smallint,                     -- WHOOP recovery or derived HRV score
  PRIMARY KEY (student_id, day)
);

------------------------------------------------------------------------
-- Student rigour: academics
------------------------------------------------------------------------

CREATE TABLE subjects (
  subject_id     bigserial PRIMARY KEY,
  student_id     text NOT NULL REFERENCES students,
  name           text NOT NULL,
  affinity       text NOT NULL CHECK (affinity IN ('likes','neutral','dislikes')),
  chapters_total smallint NOT NULL,
  UNIQUE (student_id, name)
);

CREATE TABLE chapters (
  chapter_id     bigserial PRIMARY KEY,
  subject_id     bigint NOT NULL REFERENCES subjects,
  chapter_no     smallint NOT NULL,
  title          text NOT NULL,
  planned_month  date NOT NULL                 -- month the advisor planned it for
);

-- One row each time a chapter reaches a rigour stage.
-- 1 read, 2 notes, 3 practice >70%, 4 timed past paper, 5 exam-ready >80%
CREATE TABLE chapter_stages (
  chapter_id     bigint NOT NULL REFERENCES chapters,
  stage          smallint NOT NULL CHECK (stage BETWEEN 1 AND 5),
  reached_on     date NOT NULL,
  accuracy_pct   smallint,
  PRIMARY KEY (chapter_id, stage)
);

CREATE TABLE tasks (
  task_id        bigserial PRIMARY KEY,
  student_id     text NOT NULL REFERENCES students,
  assigned_by    text NOT NULL CHECK (assigned_by IN ('advisor','self')),
  title          text NOT NULL,
  due_on         date NOT NULL,
  done_on        date,
  est_min        smallint NOT NULL,
  actual_min     smallint
);

CREATE TABLE exam_results (
  student_id     text NOT NULL REFERENCES students,
  subject        text NOT NULL,
  exam_type      text NOT NULL CHECK (exam_type IN ('formative','unit_test','half_yearly','final')),
  exam_date      date NOT NULL,
  target_pct     smallint NOT NULL,            -- set by advisor with student and parent
  target_agreed_on date,                       -- null = not yet signed off by parent
  actual_pct     smallint,
  PRIMARY KEY (student_id, subject, exam_type, exam_date)
);

------------------------------------------------------------------------
-- Program activities (week / month / quarter)
------------------------------------------------------------------------

CREATE TABLE activities (
  activity_id    text PRIMARY KEY,
  kind           text NOT NULL CHECK (kind IN (
                   'academic_session','workshop','pod','peer','mentor_call','branding',
                   'podcast','competition','parent_child','out_of_city')),
  title          text NOT NULL,
  scheduled_on   date NOT NULL,
  held           boolean NOT NULL,             -- from Google Calendar / ClickUp
  pod_id         text REFERENCES pods
);

CREATE TABLE activity_participants (
  activity_id    text NOT NULL REFERENCES activities,
  student_id     text NOT NULL REFERENCES students,
  attended       boolean NOT NULL,
  rating         smallint CHECK (rating BETWEEN 1 AND 5),   -- 1-tap in-app rating
  skill_score    numeric(3,1),                              -- facilitator form, avg of 11 soft skills (1-5)
  PRIMARY KEY (activity_id, student_id)
);

CREATE TABLE roadmap_items (
  item_id        bigserial PRIMARY KEY,
  student_id     text NOT NULL REFERENCES students,
  roadmap        text NOT NULL CHECK (roadmap IN ('career','personal','academic')),
  title          text NOT NULL,
  due_on         date NOT NULL,
  done_on        date
);

CREATE TABLE alerts (
  alert_id       bigserial PRIMARY KEY,
  student_id     text NOT NULL REFERENCES students,
  kind           text NOT NULL CHECK (kind IN ('task_overdue','subject_behind','inactive','low_quiz')),
  detail         text NOT NULL,
  raised_at      timestamptz NOT NULL,
  actioned_at    timestamptz
);

------------------------------------------------------------------------
-- Automation support
------------------------------------------------------------------------

-- OAuth tokens for cloud wearables (WHOOP, Garmin). Apple Health and Health Connect are read on the phone by the app.
CREATE TABLE wearable_tokens (
  student_id     text NOT NULL REFERENCES students,
  provider       text NOT NULL CHECK (provider IN ('whoop','garmin')),
  access_token   text NOT NULL,
  refresh_token  text,
  expires_at     timestamptz,
  PRIMARY KEY (student_id, provider)
);

-- Every automated call or message, so nothing is sent twice.
CREATE TABLE outreach_log (
  outreach_id    bigserial PRIMARY KEY,
  kind           text NOT NULL CHECK (kind IN ('discovery_reminder_24h','discovery_reminder_1h','renewal_call','advisor_alert','parent_summary')),
  ref_id         text NOT NULL,                -- lead_id, enrolment_id, advisor_id or student_id
  channel        text NOT NULL CHECK (channel IN ('smallest_ai','whatsapp')),
  sent_at        timestamptz NOT NULL DEFAULT now(),
  provider_ref   text,
  UNIQUE (kind, ref_id, sent_at)
);
CREATE INDEX outreach_ref_idx ON outreach_log (kind, ref_id);
