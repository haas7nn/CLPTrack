# Walkthrough 1: the data model and the risk score

Written 6 October 2026. Read this before the weekly explain back session. Every heading is something an
examiner could ask about.

## What exists so far

A Django project called `clptrack` with five apps. An app in Django is just a folder that holds one part of
the system.

| App | What it holds | State |
|---|---|---|
| `accounts` | The User table and the roles | Done |
| `progress` | Deliverables, submissions, meetings, actions, feedback | Done |
| `risk` | The risk score and its history | Done, formula and tests |
| `notifications` | Reminder and alert emails | Empty for now |
| `dashboard` | The pages people see | Empty for now |

## The seven tables

Each table is a Python class in a `models.py` file. Django turns the class into a database table. The
class diagram for the thesis is these seven boxes and the arrows between them.

1. **User** (`accounts/models.py`). One table for everyone. The `role` field says student, supervisor or
   coordinator. A student also has `student_id`, `section` and `supervisor`, which points at another User.
   This is simpler than three separate tables and lets one sign in page serve everybody.
2. **Deliverable** (`progress/models.py`). Something every student must hand in, with a title, a deadline
   `due_at` and an `order` for sorting. The ten CLP deadlines are loaded by the command `seed_deliverables`.
3. **Submission**. One uploaded file, linked to one student and one deliverable, with the time it was
   handed in. `days_late()` works out how many days after the deadline it arrived.
4. **Meeting**. One supervision meeting, recorded by the student: the date and what was discussed.
5. **Action**. A task agreed in a meeting, with a `done` tick. Several actions belong to one meeting.
6. **Feedback**. A written comment from a supervisor to a student, optionally attached to a submission or a
   meeting.
7. **RiskScore** (`risk/models.py`). One row per student per day: the score, the colour, and a `breakdown`
   showing what each indicator contributed. Keeping a row per day means the trend can be charted later.

Why "ForeignKey"? It is the arrow in the diagram. `Submission.student` is a ForeignKey to User, which means
each submission belongs to exactly one student.

## The risk score (`risk/scoring.py`)

The score answers one question: how much attention does this student need right now?

Five indicators, each turned into a number between 0 and 1, where 0 is no concern and 1 is the worst case:

| Indicator | Function | How the number is made | Weight |
|---|---|---|---|
| Overdue deliverables | `overdue_indicator` | Of the deliverables already past their deadline, the share with no submission | 35 |
| Submission lateness | `lateness_indicator` | Average days late across the student's submissions, divided by 7, capped at 1 | 20 |
| Supervision gap | `supervision_indicator` | Days since the last meeting, minus the 7 allowed, divided by 14, capped at 1 | 25 |
| Deadline proximity | `proximity_indicator` | If the next deadline is within 7 days and nothing is uploaded, how close it is | 10 |
| Open actions | `actions_indicator` | Share of agreed actions not yet ticked done | 10 |

Then: score = sum of (value times weight). Below 30 green, 30 to 59 amber, 60 or more red.

The weights and thresholds are read from `settings.py` if they are set there (`RISK_WEIGHTS`,
`RISK_AMBER_FROM`, `RISK_RED_FROM`), otherwise the defaults in `scoring.py` are used. That is what "stored as
settings" in the proposal means: they can be changed without touching the formula.

### The worked example

The test `test_worked_example_from_the_plan_scores_amber` in `risk/tests.py` builds this student:

* 4 deliverables due, 3 submitted, each 3 days late, 1 never submitted
* last meeting 16 days ago, with 4 agreed actions, 2 still open
* next deadline in 3 days, nothing uploaded

| Indicator | Value | Weight | Points |
|---|---|---|---|
| Overdue | 1 of 4 = 0.25 | 35 | 8.8 |
| Lateness | 3 of 7 = 0.43 | 20 | 8.6 |
| Supervision | (16 minus 7) of 14 = 0.64 | 25 | 16.1 |
| Proximity | (7 minus 3) of 7 = 0.57 | 10 | 5.7 |
| Actions | 2 of 4 = 0.50 | 10 | 5.0 |
| **Score** | | | **44, amber** |

The test asserts every one of those numbers, so if anyone changes the formula by mistake the test fails.

### One decision worth remembering

Days until the next deadline are counted as a fraction (2.5 days, not 2 or 3). The first version counted
whole days, and the test gave a different answer depending on the time of day it ran. Counting fractions is
both more accurate and more predictable. This is a good example for the "what would you do differently"
question: test with fixed times, not the clock.

## Questions an examiner might ask

* **Why one User table with a role field, not three tables?** One sign in, one set of permissions, and a
  supervisor is simply a user that students point at. Three tables would triple the code for no gain.
* **Why keep a RiskScore row per day instead of just the latest?** To chart how a student's risk changed
  over the semester, and to show in the thesis when the system first flagged someone.
* **Why these five indicators?** They are the signals a supervisor actually watches: work handed in, work
  on time, meetings happening, the next deadline, and promises kept. They were agreed with the supervisor.
* **Why those weights?** Starting values from judgement, with overdue work and missed meetings weighted
  highest because they are the strongest signs. They are settings, so they can be adjusted after real use.
* **What happens for a brand new student with nothing due?** Overdue, lateness, proximity and actions are
  all 0. Only the supervision gap counts, measured from the semester start, so a student who has never
  recorded a meeting slowly turns amber. That is intended.

## Commands you should be able to run

    .venv/bin/python manage.py test                 # runs the tests
    .venv/bin/python manage.py seed_deliverables    # loads the ten CLP deadlines
    .venv/bin/python manage.py seed_demo            # creates sample accounts
    .venv/bin/python manage.py runserver            # starts the site at http://127.0.0.1:8000
