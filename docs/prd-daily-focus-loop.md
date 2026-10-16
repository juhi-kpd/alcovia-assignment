# PRD: Daily focus loop

| | |
| --- | --- |
| Owner | Product, Systems & Analytics Lead |
| Team | 1 full-stack engineer, 1 process designer |
| Status | Draft for week 1 (from 1 Nov) |
| Target release | Week 5 (to 5 students), week 6 (everyone) |

## Problem

Students open the Alcovia app for about 2.15 minutes a day on average. The goal is 30. Over the last 45 days, 20 students used the app; 7 have not opened it in two weeks. Everyone uses Home and most play the Realm, but study features drop off fast: 10 students opened the Syllabus, only 1 this week. The Focus Timer was tried by 11 and kept by 5.

From using the app as a new student:

- About 22 taps of intro screens and tooltips before anything useful.
- Studying and the Realm game feel like two separate apps. Nothing on a chapter says it earns Realm progress.
- Home shows advisor-style numbers ("Daily Velocity 0.4% / 1.33%") that a teen does not act on.
- Tasks shows "101 of 155 done", which reads as being behind.

## Goal and metric

| Metric | Now | 30 Nov | 31 Dec | 31 Jan |
| --- | --- | --- | --- | --- |
| Average active minutes a day (incl. focus) | 2.15 | 10 | 20 | 30 |
| Students doing 1+ focus session a day | ~5 of 20 | 8 | 10 | 12 |
| Students active in the week | 11–17 of 20 | 15 | 17 | 18 |

Guardrail: focus sessions abandoned before the end stay under 30%.

The one metric that decides scale / improve / stop: **average active minutes a day**, read weekly in Mixpanel.

## Who it is for

A 14–17 year old Alcovian with school, tuition and activities, who opens the app for the Realm and has an advisor setting their weekly academic plan.

## The loop

Open the app → see today's one task → start a focus session on it → earn Realm progress → mark the chapter stage done → see how the pod is doing.

## Scope

**In**

1. **Onboarding in 3 screens:** pick a goal, see today's task, start a first 10-minute focus session. Other features are explained the first time a student opens them.
2. **Today card on Home:** one task chosen by the advisor (a chapter and its next rigour stage), a Start focus button, the 8pm quiz, and the pod's progress. Everything else moves one level down.
3. **Focus session tied to a chapter:** starting from the Today card links the session to the chapter. Finishing it shows the Realm reward ("+1 territory") and asks one question: "Did you finish this stage?"
4. **8pm quiz inside the app**, with a push notification at 7:55 pm.
5. **Pod leaderboard:** focus minutes this week among the 5 pod members, not all students.
6. **Plain words:** "1 more chapter today to stay on track" instead of velocity percentages; Tasks shows today's 3, not the full list.

**Out (for now)**

- Phone-locking focus mode (separate feasibility check in week 1; needs Apple Screen Time API approval on iOS).
- Wellness changes beyond hiding the WHOOP prompt when no wearable is connected.
- New Realm content.

## Requirements

| # | Requirement | Owner |
| --- | --- | --- |
| R1 | Advisors can set one "today" task per student per day, from ClickUp or the advisor view | Process designer + engineer |
| R2 | If no advisor task exists, the app picks the next chapter stage in the subject furthest behind pace | Engineer |
| R3 | Focus session stores `chapter_id`, planned and actual minutes, completed yes/no | Engineer |
| R4 | Realm reward for a completed session is shown on the Today card before starting | Engineer |
| R5 | Quiz attempts are stored per student per day | Engineer |
| R6 | n8n sends a nudge 15 minutes before the student's usual study slot if no session has started | Process designer |
| R7 | Onboarding can be skipped in one tap and never shows again | Engineer |

## Tracking (Mixpanel)

| Event | Properties |
| --- | --- |
| `onboarding_step_viewed` | step (1–3), skipped |
| `today_card_viewed` | task_source (advisor / auto), subject, stage |
| `focus_started` | planned_min, chapter_id, from (today_card / timer) |
| `focus_finished` | actual_min, completed, realm_reward |
| `chapter_stage_marked` | chapter_id, stage, from (focus_end / syllabus) |
| `quiz_submitted` | correct, seconds_taken |
| `pod_board_viewed` | rank_in_pod |

Events are written into `focus_sessions`, `quiz_attempts`, `chapter_stages` and `app_usage_daily` (see `db/schema.sql`) so the student tracker updates without manual entry.

## Release plan

1. Week 2–3: build onboarding and Today card; test a clickable mock with 3 students (gate: all 3 start a focus session without help).
2. Week 4–5: focus-to-chapter link, quiz, pod board; release to 5 students.
3. Week 6: release to everyone if minutes a day for the 5 are not lower than before.
4. Weeks 6–8: weekly review; one change at a time so its effect can be seen.

With 20 students an A/B test can't give a reliable answer, so each change is judged by its before-and-after trend over 2–3 weeks plus short conversations with 5 students.

## Risks

- **Advisors don't set daily tasks.** Fallback R2 picks one automatically; advisor input rate is tracked on the student dashboard.
- **Rewards feel small.** Coins are currently in the hundreds of thousands, so +50 means nothing. Rescale so one session is a visible jump.
- **Students game the timer.** Count a session only if the app stays open; flag sessions with no stage progress over two weeks.

## Open questions

- Is 30 minutes a day the right target, or should it be "one completed focus session a day"? The second may be a better measure of study habit.
- Should parents see focus minutes daily or only in the weekly summary?
