"""Generate dummy-but-consistent seed data for the Alcovia database.

Writes:
  db/seed.sql                          INSERTs for every table in db/schema.sql
  dashboards/data/student-tracker.json the same student data, shaped for the student dashboard

GTM monthly totals match the constants in dashboards/gtm-tracker.html, so the SQL
metric queries and the dashboard show the same numbers. All names and figures are fictional.
Run:  python3 scripts/generate_seed.py
"""
import json, math, random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = random.Random(7)
TODAY = date(2026, 10, 16)

PRICE = {"trial": 45000, "full": 180000, "seat": 3999}

# ---------------------------------------------------------------- GTM constants
# month, target, trial, full, seats, meta, organic, qual, dset, dshow, amb, arch, spendP, spendW, journey days
MONTHS = [
    (date(2026, 5, 1), 500000, 2, 1, 34, 140, 18, 48, 27, 19, 14, 8, 120000, 30000, 18),
    (date(2026, 6, 1), 550000, 3, 1, 41, 155, 20, 54, 30, 22, 16, 9, 130000, 32000, 17),
    (date(2026, 7, 1), 650000, 3, 2, 38, 170, 22, 60, 34, 25, 18, 11, 140000, 31000, 19),
    (date(2026, 8, 1), 750000, 4, 2, 52, 205, 26, 72, 40, 31, 23, 13, 160000, 38000, 16),
    (date(2026, 9, 1), 850000, 5, 2, 47, 220, 28, 78, 44, 33, 25, 14, 170000, 39000, 15),
    (date(2026, 10, 1), 900000, 3, 1, 29, 120, 15, 42, 23, 16, 12, 7, 90000, 22000, 14),
]
CAMPAIGNS = [
    ("cmp_career", "Program · Career clarity", "program"),
    ("cmp_parents", "Program · Parents 35–50", "program"),
    ("cmp_trial", "Program · Trial push", "program"),
    ("cmp_workshop", "Workshop · Fortnightly", "workshop"),
]
# id, campaign, name, format, page, spend share, result share, ctr by month, frequency by month
CREATIVES = [
    ("ad_reel_25", "cmp_career", 'Reel: "What will you be at 25?"', "reel", "/career-program", .30, .36, [1.9, 1.9, 1.8, 1.8, 1.7, 1.7], [1.4, 1.6, 1.7, 1.9, 2.1, 2.2]),
    ("ad_carousel_day", "cmp_career", "Carousel: a day as an Alcovian", "carousel", "/career-program", .22, .25, [1.5, 1.5, 1.4, 1.4, 1.3, 1.3], [1.6, 1.9, 2.2, 2.4, 2.6, 2.7]),
    ("ad_parent_video", "cmp_parents", "Parent testimonial video", "video", "/career-program", .20, .21, [1.4, 1.3, 1.2, 1.0, 0.9, 0.8], [1.8, 2.3, 2.7, 3.1, 3.4, 3.6]),
    ("ad_top1_banner", "cmp_parents", 'Static: "Top 1% students" banner', "static", "/career-program", .16, .08, [0.8, 0.8, 0.7, 0.7, 0.6, 0.6], [1.5, 1.8, 2.0, 2.2, 2.4, 2.5]),
    ("ad_trial_offer", "cmp_trial", "Static: 3-month trial offer", "static", "/trial-offer", .12, .10, [1.2, 1.2, 1.1, 1.1, 1.0, 1.0], [1.2, 1.4, 1.6, 1.8, 2.0, 2.1]),
    ("ad_ws_reel", "cmp_workshop", "Reel: workshop highlights", "reel", "/workshop-signup", .55, .62, [2.1, 2.1, 2.0, 2.0, 1.9, 1.9], [1.3, 1.5, 1.6, 1.8, 1.9, 2.0]),
    ("ad_ws_poster", "cmp_workshop", "Static: guest speaker poster", "static", "/workshop-signup", .45, .38, [1.1, 1.0, 0.9, 0.8, 0.8, 0.7], [1.9, 2.4, 2.8, 3.0, 3.2, 3.4]),
]
PAGES = {
    "/career-program": ([1050, 1160, 1240, 1480, 1560, 860], [58, 59, 61, 60, 62, 63], [2.1, 2.1, 2.2, 2.2, 2.3, 2.3]),
    "/trial-offer": ([300, 330, 350, 420, 440, 250], [66, 67, 69, 71, 72, 74], [2.6, 2.7, 2.9, 3.1, 3.3, 3.4]),
    "/workshop-signup": ([1650, 1790, 1720, 2100, 2050, 1260], [49, 48, 50, 49, 51, 50], [1.7, 1.8, 1.7, 1.8, 1.8, 1.9]),
}
CPM = 180.0  # ₹ per 1000 impressions

def month_end(m):
    if m.month == 10 and m.year == 2026:
        return TODAY
    nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return nxt - timedelta(days=1)

def days_in(m):
    d, e = m, month_end(m)
    while d <= e:
        yield d
        d += timedelta(days=1)

def split_int(total, n):
    """Split an integer total into n near-equal integer parts."""
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]

def ts(d, hour=10, minute=0):
    return datetime(d.year, d.month, d.day, hour, minute)

# ---------------------------------------------------------------- SQL writer
rows = {}
def add(table, cols, values):
    rows.setdefault(table, (cols, []))[1].append(values)

def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        return repr(round(v, 2))
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "+05:30'"
    if isinstance(v, date):
        return "'" + v.isoformat() + "'"
    return "'" + str(v).replace("'", "''") + "'"

# ---------------------------------------------------------------- GTM data
for c in CAMPAIGNS:
    add("campaigns", ("campaign_id", "name", "objective"), c)
for c in CREATIVES:
    add("creatives", ("creative_id", "campaign_id", "name", "format", "landing_page"), (c[0], c[1], c[2], c[3], c[4]))

program_creatives = [c for c in CREATIVES if c[1] != "cmp_workshop"]
ws_creatives = [c for c in CREATIVES if c[1] == "cmp_workshop"]
lead_n = 0
workshop_n = 0
pay_n = 0
for mi, (m, target, trial, full, seats, meta, org, qual, dset, dshow, amb, arch, spendP, spendW, jdays) in enumerate(MONTHS):
    add("revenue_targets", ("month", "target_inr"), (m, target))
    days = list(days_in(m))
    # ad spend per creative, spread evenly over the month's days
    for c in CREATIVES:
        mspend = (spendP if c[1] != "cmp_workshop" else spendW) * c[5]
        impressions = mspend / CPM * 1000
        clicks = impressions * c[7][mi] / 100
        reach = impressions / c[8][mi]
        for d, sp, im, cl, rc in zip(days, split_int(round(mspend), len(days)), split_int(round(impressions), len(days)),
                                     split_int(round(clicks), len(days)), split_int(round(reach), len(days))):
            add("ad_daily", ("creative_id", "day", "spend_inr", "impressions", "reach", "link_clicks"), (c[0], d, sp, im, rc, cl))
    for page, (visits, drop, load) in PAGES.items():
        for d, v in zip(days, split_int(visits[mi], len(days))):
            add("landing_page_daily", ("page", "day", "visits", "conversions", "mobile_load_s"),
                (page, d, v, round(v * (100 - drop[mi]) / 100), load[mi]))
    # leads: nested stage counts; paid leads created early so they pay inside the month
    total = meta + org
    paid = trial + full
    stage_counts = [total, qual, dset, dshow, amb, arch, paid]
    stage_cols = ["created_at", "qualified_at", "discovery_set_at", "discovery_showed_at", "ambition_done_at", "architect_done_at", "paid_at"]
    drop_names = ["lead", "qualified", "discovery_set", "discovery_showed", "ambition_done", "architect_done"]
    # assign creatives to meta leads in proportion to result share
    weights = [c[6] for c in program_creatives]
    for i in range(total):
        lead_n += 1
        reached = sum(1 for s in stage_counts if i < s)  # leads earlier in the list go deeper
        source = "organic" if i % (total // org) == 0 and i // (total // org) < org else "meta"
        creative = None if source == "organic" else R.choices(program_creatives, weights)[0][0]
        last_day = month_end(m).day
        if reached == 7:
            jd = jdays + R.randint(-1, 1)
            start = max(1, min(R.randint(1, 10), last_day - jd))
        else:
            jd = None
            start = R.randint(1, last_day)
        created = date(m.year, m.month, start)
        stamps = {"created_at": ts(created, R.randint(8, 21), R.randint(0, 59))}
        if reached == 7:
            offsets = sorted(R.sample(range(1, jd), 5)) + [jd]
        else:
            offsets = sorted(R.sample(range(1, 20), 5))
        for k in range(1, reached):
            d = created + timedelta(days=offsets[k - 1])
            stamps[stage_cols[k]] = ts(min(d, TODAY), 11 + k)
        dropped_at, drop_stage = None, None
        if reached < 7:
            dd = created + timedelta(days=(offsets[reached - 2] if reached > 1 else 0) + R.randint(3, 10))
            if dd <= TODAY:
                dropped_at, drop_stage = ts(dd, 18), drop_names[reached - 1]
        add("leads", ("lead_id", "source", "creative_id", "created_at", *stage_cols[1:], "dropped_at", "drop_stage"),
            (f"L{lead_n:05d}", source, creative, stamps["created_at"], *[stamps.get(c) for c in stage_cols[1:]], dropped_at, drop_stage))
        if reached == 7:
            product = "trial" if (i - 0) < trial else "full"
            pay_n += 1
            add("payments", ("payment_id", "product", "invoice_id", "workshop_id", "student_id", "utm_creative_id", "amount_inr", "paid_at"),
                (f"pay_{pay_n:05d}", product, None, None, None, creative, PRICE[product], stamps["paid_at"]))
    # workshops: two a month (one so far in October), seats split between them
    ws_days = [8, 22] if m.month != 10 else [10]
    for d_, s_ in zip(ws_days, split_int(seats, len(ws_days))):
        workshop_n += 1
        wid = f"ws_{workshop_n:02d}"
        add("workshops", ("workshop_id", "title", "held_on", "seat_price_inr"), (wid, f"Career workshop #{workshop_n}", date(m.year, m.month, d_), PRICE["seat"]))
        for _ in range(s_):
            pay_n += 1
            pd = date(m.year, m.month, max(1, d_ - R.randint(0, 6)))
            ws_creative = R.choices(ws_creatives, [c[6] for c in ws_creatives])[0][0]
            add("payments", ("payment_id", "product", "invoice_id", "workshop_id", "student_id", "utm_creative_id", "amount_inr", "paid_at"),
                (f"pay_{pay_n:05d}", "workshop", None, wid, None, ws_creative, PRICE["seat"], ts(pd, R.randint(9, 22))))

# ---------------------------------------------------------------- people
ADVISORS = [("adv_ritika", "Ritika"), ("adv_karan", "Karan"), ("adv_meera", "Meera")]
PODS = [("pod_orion", "Orion"), ("pod_lyra", "Lyra"), ("pod_vega", "Vega"), ("pod_draco", "Draco")]
NAMES = ["Anaya T.", "Reyansh B.", "Diya G.", "Arjun N.", "Kiara V.", "Ishaan P.", "Myra K.", "Vivaan R.", "Saanvi J.", "Kabir R.",
         "Aditi L.", "Rohan C.", "Tara S.", "Neel D.", "Meher A.", "Dev K.", "Zara H.", "Ira P.", "Yash M.", "Sara D."]
for a in ADVISORS:
    add("advisors", ("advisor_id", "name"), a)
for p in PODS:
    add("pods", ("pod_id", "name"), p)

START = date(2026, 8, 1)
DAYS = [START + timedelta(days=i) for i in range((TODAY - START).days + 1)]
WEARABLES = {2: "whoop", 5: "apple_health", 8: "health_connect", 11: "apple_health", 14: "garmin", 17: "health_connect"}
SUBJECTS = ["Maths", "Physics", "Chemistry", "Biology", "English", "History"]
LAPSED = {3, 7, 9, 12, 15, 18, 19}   # 7 students silent for the last two weeks (as in the brief)

students = []
for i, name in enumerate(NAMES):
    sid = f"S{i + 1:02d}"
    engage = round(R.uniform(0.2, 0.95), 2)
    skill = round(R.uniform(0.3, 0.9), 2)
    last_active = TODAY - timedelta(days=R.randint(15, 30)) if i in LAPSED else TODAY - timedelta(days=R.randint(0, 3))
    plan = "trial" if i < 8 else "full"
    st = dict(id=sid, name=name, grade=R.choice([9, 10, 11]), advisor=ADVISORS[i % 3][0], pod=PODS[i // 5][0],
              joined=date(2026, R.choice([4, 5, 6, 7]), R.randint(1, 28)), wearable=WEARABLES.get(i), engage=engage,
              skill=skill, last_active=last_active, plan=plan)
    students.append(st)
    add("students", ("student_id", "lead_id", "name", "grade", "advisor_id", "pod_id", "joined_on", "wearable"),
        (sid, None, name, st["grade"], st["advisor"], st["pod"], st["joined"], st["wearable"]))

# enrolments: first 5 trials end in the next 30 days (renewal list), others ended / full program
TRIAL_ENDS = [date(2026, 10, 20), date(2026, 10, 27), date(2026, 11, 3), date(2026, 11, 10), date(2026, 11, 12)]
for i, st in enumerate(students):
    if i < 5:
        end = TRIAL_ENDS[i]; start = end - timedelta(days=92)
        add("enrolments", ("enrolment_id", "student_id", "plan", "start_on", "end_on", "renewed"), (f"en_{i+1:02d}", st["id"], "trial", start, end, False))
    elif i < 8:
        start = date(2026, 7, R.randint(1, 15)); end = start + timedelta(days=92)
        add("enrolments", ("enrolment_id", "student_id", "plan", "start_on", "end_on", "renewed"), (f"en_{i+1:02d}", st["id"], "trial", start, end, False))
    else:
        start = st["joined"]; end = date(2027, 3, 31)
        add("enrolments", ("enrolment_id", "student_id", "plan", "start_on", "end_on", "renewed"), (f"en_{i+1:02d}", st["id"], "full", start, end, False))

# invoices: the unpaid list shown on the GTM tracker plus some paid ones
UNPAID = [("INV-0412", "Parent of Aarav S.", "full", date(2026, 7, 28)), ("INV-0447", "Parent of Myra K.", "trial", date(2026, 8, 19)),
          ("INV-0471", "Parent of Kabir R.", "full", date(2026, 9, 8)), ("INV-0483", "Parent of Ira P.", "trial", date(2026, 9, 24)),
          ("INV-0496", "Parent of Vihaan M.", "trial", date(2026, 10, 6)), ("INV-0502", "Parent of Sara D.", "full", date(2026, 10, 13))]
for inv, who, prod, d in UNPAID:
    add("invoices", ("invoice_id", "student_id", "billed_to", "product", "amount_inr", "issued_on", "due_on", "paid_on"),
        (inv, None, who, prod, PRICE[prod], d, d + timedelta(days=7), None))

# ---------------------------------------------------------------- day-level student data
quiz_topics = ["Sports", "History", "Logical reasoning", "Brand logos", "Science", "Geography", "Current affairs"]
skipped_quiz = {date(2026, 8, 15), date(2026, 9, 5), date(2026, 10, 2)}
for d in DAYS:
    if d not in skipped_quiz:
        add("quizzes", ("quiz_date", "topic", "questions"), (d, quiz_topics[d.toordinal() % 7], 10))

session_rows = []
daily = {}
for st in students:
    sid, e = st["id"], st["engage"]
    arr = dict(app=[], focus=[], quiz=[], plan=[], done=[], active=[], sleep=[], recovery=[])
    for d in DAYS:
        alive = d <= st["last_active"]
        # app minutes: overall mean lands near the brief's 2.15 min/day
        on = alive and R.random() < 0.25 + 0.55 * e
        app = round(R.lognormvariate(1.3, 0.6) * (0.3 + e), 1) if on else 0.0
        focus = 0
        if on and R.random() < 0.02 + 0.13 * e:
            planned = R.choice([15, 25, 25, 30])
            completed = R.random() < 0.6 + 0.35 * e
            actual = planned if completed else R.randint(3, planned - 2)
            focus = actual
            session_rows.append((sid, ts(d, R.choice([16, 17, 18, 19, 20]), R.randint(0, 59)), planned, actual, completed))
        app = round(app + focus * 0.9, 1)  # the app is open during a focus session
        if app:
            add("app_usage_daily", ("student_id", "day", "active_minutes"), (sid, d, app))
        q = None
        if d not in skipped_quiz and alive and R.random() < 0.2 + 0.6 * e:
            q = max(0, min(10, round(R.gauss(4 + 4 * st["skill"], 1.5))))
            add("quiz_attempts", ("quiz_date", "student_id", "correct"), (d, sid, q))
        planned_min, done_min = 0, 0
        if d.weekday() < 6:
            for slot, mins, p_done in (("self_study", R.choice([60, 75, 90]), 0.15 + 0.75 * e if alive else 0.05),
                                       ("tuition", 90, 0.92), ("extracurricular", 60, 0.85)):
                if slot != "tuition" or d.weekday() in (0, 2, 4):
                    done = R.random() < p_done
                    add("timetable_slots", ("student_id", "day", "slot_type", "planned_min", "done"), (sid, d, slot, mins, done))
                    if slot == "self_study":
                        planned_min, done_min = mins, (mins if done else 0)
        act = sl = rec = None
        if st["wearable"] and alive:
            act = max(5, round(R.gauss(48, 18)))
            sl = round(max(4.5, min(9.5, R.gauss(7.1, 0.8))), 1)
            rec = max(15, min(99, round(R.gauss(62, 15))))
            add("wearable_daily", ("student_id", "day", "source", "active_min", "sleep_hours", "recovery_pct"), (sid, d, st["wearable"], act, sl, rec))
        arr["app"].append(app); arr["focus"].append(focus); arr["quiz"].append(q)
        arr["plan"].append(planned_min); arr["done"].append(done_min)
        arr["active"].append(act); arr["sleep"].append(sl); arr["recovery"].append(rec)
    daily[sid] = arr
for s in session_rows:
    add("focus_sessions", ("student_id", "started_at", "planned_min", "actual_min", "completed"), s)

# ---------------------------------------------------------------- academics
subject_id = chapter_id = task_id = 0
acad = {}
expected_frac = 0.5 + 0.25 * (TODAY - date(2026, 10, 1)).days / 92   # 25% a quarter from 1 April
for st in students:
    sid, e, sk = st["id"], st["engage"], st["skill"]
    acad[sid] = dict(subjects=[], tasks=[], exams=[])
    for sub in SUBJECTS:
        subject_id += 1
        total = R.randint(12, 16)
        affinity = R.choice(["likes", "neutral", "neutral", "dislikes"])
        add("subjects", ("subject_id", "student_id", "name", "affinity", "chapters_total"), (subject_id, sid, sub, affinity, total))
        pace = max(0.1, min(1.15, R.gauss(0.55 + 0.5 * e, 0.12)))  # share of expected chapters started
        started = min(total, round(total * expected_frac * pace))
        stage_counts = [0] * 5
        for c in range(1, total + 1):
            chapter_id += 1
            planned = date(2026, 4, 1) + timedelta(days=int((c - 1) * 365 / total))
            planned = date(planned.year, planned.month, 1)
            add("chapters", ("chapter_id", "subject_id", "chapter_no", "title", "planned_month"), (chapter_id, subject_id, c, f"{sub} chapter {c}", planned))
            if c <= started:
                depth = 1 + sum(R.random() < (0.35 + 0.55 * (e + sk) / 2) for _ in range(4))
                d0 = planned + timedelta(days=R.randint(5, 40))
                d0 = min(d0, TODAY - timedelta(days=5))
                for s_ in range(1, depth + 1):
                    acc = None
                    if s_ == 3: acc = R.randint(71, 90)
                    if s_ == 4: acc = R.randint(60, 85)
                    if s_ == 5: acc = R.randint(81, 95)
                    add("chapter_stages", ("chapter_id", "stage", "reached_on", "accuracy_pct"), (chapter_id, s_, min(TODAY, d0 + timedelta(days=4 * (s_ - 1))), acc))
                    stage_counts[s_ - 1] += 1
        readiness = round(sum(stage_counts) * 20 / total)          # chapter readiness, 0–100 per subject
        done_pct = round(100 * started / total)
        acad[sid]["subjects"].append(dict(name=sub, affinity=affinity, total=total, started=started, done_pct=done_pct,
                                          expected_pct=round(100 * expected_frac), readiness=readiness, stages=stage_counts))
        # exams: unit test (July) and half-yearly (September)
        for etype, edate in (("unit_test", date(2026, 7, 20)), ("half_yearly", date(2026, 9, 22))):
            target = R.choice([70, 75, 80, 85, 90])
            actual = max(35, min(99, round(target + R.gauss(-12 + 18 * sk, 7))))
            agreed = None if st["id"] in ("S04", "S13", "S19") else date(2026, 6, 25)
            add("exam_results", ("student_id", "subject", "exam_type", "exam_date", "target_pct", "target_agreed_on", "actual_pct"),
                (sid, sub, etype, edate, target, agreed, actual))
            acad[sid]["exams"].append(dict(subject=sub, type=etype, date=edate.isoformat(), target=target, actual=actual))
    # tasks: about 4 advisor tasks a week
    d = START
    while d <= TODAY:
        for _ in range(4):
            task_id += 1
            due = d + timedelta(days=R.randint(1, 6))
            est = R.choice([30, 45, 60, 90])
            alive = due <= st["last_active"] + timedelta(days=2)
            done_on = None; actual = None
            if due <= TODAY and alive and R.random() < 0.3 + 0.65 * e:
                done_on = due + timedelta(days=R.choice([-2, -1, 0, 0, 0, 1, 2, 4]) if R.random() > e * 0.6 else -1)
                done_on = min(done_on, TODAY)
                actual = max(10, round(est * R.gauss(1.25 - 0.3 * e, 0.25)))
            add("tasks", ("student_id", "assigned_by", "title", "due_on", "done_on", "est_min", "actual_min"),
                (sid, "advisor", R.choice(["Revise", "Practice set", "Past paper", "Notes"]) + " – " + R.choice(SUBJECTS), due, done_on, est, actual))
            acad[sid]["tasks"].append(dict(due=due.isoformat(), done=done_on.isoformat() if done_on else None, est=est, actual=actual))
        d += timedelta(days=7)

# ---------------------------------------------------------------- program activities
acts = []   # (id, kind, title, date, held, pod, participants{sid: (attended, rating, skill)})
def activity(aid, kind, title, d, held, pod, sids, p_attend=None, skill=False):
    parts = {}
    for sid in sids:
        st = next(s for s in students if s["id"] == sid)
        alive = d <= st["last_active"] + timedelta(days=3)
        pa = p_attend if p_attend is not None else 0.45 + 0.5 * st["engage"]
        att = held and d <= TODAY and alive and R.random() < pa
        rating = max(1, min(5, round(R.gauss(3.6 + st["engage"], 0.7)))) if att and R.random() < 0.55 + 0.4 * st["engage"] else None
        sks = round(max(1.0, min(5.0, R.gauss(2.6 + 2 * st["skill"], 0.4))), 1) if att and skill else None
        parts[sid] = (att, rating, sks)
    acts.append((aid, kind, title, d, held, pod, parts))

all_ids = [s["id"] for s in students]
n = 0
for st in students:      # academic sessions: twice a week with the advisor
    d = START
    while d <= TODAY:
        for off in (1, 4):
            dd = d + timedelta(days=off)
            if dd <= TODAY:
                n += 1
                activity(f"as_{n:04d}", "academic_session", "Academic session", dd, R.random() < 0.93, None, [st["id"]], p_attend=0.75 + 0.25 * st["engage"])
        d += timedelta(days=7)
for i, wd in enumerate([date(2026, 8, 8), date(2026, 8, 22), date(2026, 9, 5), date(2026, 9, 19), date(2026, 10, 10)]):
    activity(f"wk_{i+1:02d}", "workshop", f"Career workshop #{i+1}", wd, True, None, all_ids, skill=True)
for pi, (pid, _) in enumerate(PODS):
    members = [s["id"] for s in students if s["pod"] == pid]
    for mi, md in enumerate([date(2026, 8, 16), date(2026, 9, 13), date(2026, 10, 11)]):
        held = not (pid == "pod_vega" and mi == 1)
        activity(f"pod_{pi}_{mi}", "pod", "Pod session", md + timedelta(days=pi), held, pid, members)
for mi, m in enumerate([8, 9, 10]):
    pairs = R.sample(all_ids, 8)
    for k in range(0, 8, 2):
        dd = date(2026, m, R.randint(3, 14 if m == 10 else 26))
        activity(f"peer_{m}_{k}", "peer", "Peer session", dd, R.random() < 0.85, None, pairs[k:k + 2])
    for st in students:
        dd = date(2026, m, R.randint(5, 15 if m == 10 else 25))
        activity(f"mc_{m}_{st['id']}", "mentor_call", "Mentor call", dd, R.random() < 0.85, None, [st["id"]], p_attend=0.9)
        dd = date(2026, m, R.randint(5, 15 if m == 10 else 25))
        activity(f"br_{m}_{st['id']}", "branding", "Personal branding shoot", dd, R.random() < 0.7, None, [st["id"]], p_attend=0.9)
activity("q2_podcast", "podcast", "Podcast: founder of an edtech startup", date(2026, 9, 26), True, None, R.sample(all_ids, 4), p_attend=1)
activity("q2_competition", "competition", "Inter-school debate (prep)", date(2026, 9, 28), True, None, R.sample(all_ids, 5), p_attend=1)
activity("q2_parent_child", "parent_child", "Parent-child build day", date(2026, 8, 30), True, None, all_ids)
activity("q2_out_of_city", "out_of_city", "Lonavala leadership trip", date(2026, 9, 12), True, None, all_ids)
for aid, kind, title, d, held, pod, parts in acts:
    add("activities", ("activity_id", "kind", "title", "scheduled_on", "held", "pod_id"), (aid, kind, title, d, held, pod))
    for sid, (att, rating, sks) in parts.items():
        add("activity_participants", ("activity_id", "student_id", "attended", "rating", "skill_score"), (aid, sid, att, rating, sks))

# ---------------------------------------------------------------- roadmaps and alerts
roadmaps = {}
alert_rows = []
for st in students:
    sid, e = st["id"], st["engage"]
    items = []
    done = R.random() < 0.3 + 0.7 * e
    items.append(("career", "Career roadmap v1 agreed", date(2026, 9, 30), date(2026, 9, R.randint(10, 29)) if done else None))
    for m, label in ((8, "Aug"), (9, "Sep"), (10, "Oct")):
        due = date(2026, m, 28) if m != 10 else date(2026, 10, 31)
        hit = due <= TODAY and R.random() < 0.25 + 0.7 * e
        items.append(("personal", f"{label} personal milestone", due, due - timedelta(days=R.randint(0, 6)) if hit else None))
    items.append(("academic", "Half-yearly targets set", date(2026, 8, 31), date(2026, 8, R.randint(10, 30)) if R.random() < 0.85 else None))
    for it in items:
        add("roadmap_items", ("student_id", "roadmap", "title", "due_on", "done_on"), (sid, *it))
    roadmaps[sid] = [dict(roadmap=a, title=b, due=c.isoformat(), done=d.isoformat() if d else None) for a, b, c, d in items]
    # alerts derived from the data
    overdue = [t for t in acad[sid]["tasks"] if not t["done"] and date.fromisoformat(t["due"]) < TODAY - timedelta(days=3)]
    if overdue:
        alert_rows.append((sid, "task_overdue", f"{len(overdue)} tasks more than 3 days overdue"))
    for sub in acad[sid]["subjects"]:
        if sub["expected_pct"] - sub["done_pct"] > 15:
            alert_rows.append((sid, "subject_behind", f"{sub['name']} {sub['done_pct']}% done vs {sub['expected_pct']}% expected"))
    if (TODAY - st["last_active"]).days >= 7:
        alert_rows.append((sid, "inactive", f"No app activity for {(TODAY - st['last_active']).days} days"))
alerts_json = {}
for sid, kind, detail in alert_rows:
    raised = ts(TODAY - timedelta(days=R.randint(0, 6)), 21)
    actioned = raised + timedelta(hours=R.randint(4, 70)) if R.random() < 0.7 else None
    if actioned and actioned > datetime(2026, 10, 16, 23, 0):
        actioned = None
    add("alerts", ("student_id", "kind", "detail", "raised_at", "actioned_at"), (sid, kind, detail, raised, actioned))
    alerts_json.setdefault(sid, []).append(dict(kind=kind, detail=detail, raised=raised.date().isoformat(), actioned=actioned is not None))

# ---------------------------------------------------------------- write seed.sql
order = ["campaigns", "creatives", "ad_daily", "landing_page_daily", "leads", "revenue_targets", "advisors", "pods", "students",
         "enrolments", "workshops", "invoices", "payments", "app_usage_daily", "focus_sessions", "quizzes", "quiz_attempts",
         "timetable_slots", "wearable_daily", "subjects", "chapters", "chapter_stages", "tasks", "exam_results", "activities",
         "activity_participants", "roadmap_items", "alerts"]
out = ["-- Generated by scripts/generate_seed.py. Dummy data; all names are fictional.", "SET search_path TO alcovia;", "BEGIN;"]
for t in order:
    cols, vals = rows[t]
    for i in range(0, len(vals), 500):
        chunk = vals[i:i + 500]
        out.append(f"INSERT INTO {t} ({', '.join(cols)}) VALUES\n" + ",\n".join("(" + ", ".join(lit(v) for v in r) + ")" for r in chunk) + ";")
out += ["SELECT setval(pg_get_serial_sequence('alcovia.subjects','subject_id'), (SELECT max(subject_id) FROM alcovia.subjects));",
        "SELECT setval(pg_get_serial_sequence('alcovia.chapters','chapter_id'), (SELECT max(chapter_id) FROM alcovia.chapters));",
        "COMMIT;"]
(ROOT / "db" / "seed.sql").write_text("\n".join(out) + "\n")

# ---------------------------------------------------------------- write dashboard JSON
act_json = [dict(id=a, kind=k, title=t, date=d.isoformat(), held=h,
                 p={sid: [int(att), r, s] for sid, (att, r, s) in parts.items()}) for a, k, t, d, h, _, parts in acts]
student_json = dict(
    generated=TODAY.isoformat(), start=START.isoformat(),
    advisors=dict(ADVISORS), pods=dict(PODS),
    quiz_held=[int(d not in skipped_quiz) for d in DAYS],
    students=[dict(id=s["id"], name=s["name"], grade=s["grade"], advisor=s["advisor"], pod=s["pod"], plan=s["plan"],
                   wearable=s["wearable"], last_active=s["last_active"].isoformat(), daily=daily[s["id"]],
                   subjects=acad[s["id"]]["subjects"], exams=acad[s["id"]]["exams"], tasks=acad[s["id"]]["tasks"],
                   roadmaps=roadmaps[s["id"]], alerts=alerts_json.get(s["id"], []),
                   targets_agreed=s["id"] not in ("S04", "S13", "S19")) for s in students],
    activities=act_json)
(ROOT / "dashboards" / "data").mkdir(parents=True, exist_ok=True)
(ROOT / "dashboards" / "data" / "student-tracker.json").write_text(json.dumps(student_json, separators=(",", ":")))

all_app = [v for s in daily.values() for v in s["app"]]
print("rows:", {t: len(rows[t][1]) for t in order})
print("avg app minutes/day (Aug–Oct):", round(sum(all_app) / len(all_app), 2))
