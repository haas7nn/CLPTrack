# Walkthrough 10: score settings, adding people, passwords and the printable report

Written 13 October 2026. Four additions, each small, each answering a question an examiner would ask.

## 1. Score settings, with a what if preview

Question it answers: how do you justify the weights, and who can change them?

The coordinator opens Score settings. The page shows the five weights and the two cut off points.
Preview works out every student's score twice, once with the saved values and once with the typed
ones, and lists who would change colour. Nothing is saved. Save stores the values and runs the daily
scoring straight away.

Where: `ScoreSettings` in `risk/models.py` is one row. `scoring.weights()` and `scoring.thresholds()`
read that row, and fall back to the starting values if it does not exist. `scoring.compute()` takes two
optional arguments, `use_weights` and `cutoffs`, which only the preview passes. The form checks that
the five weights add up to 100 and that amber starts below red.

The sentence under every "Why this score" table reads the cut off points from `risk/context.py`, so it
is never wrong after a change.

## 2. Add people from a csv file

Question it answers: how do 87 students get into the system?

The coordinator opens Add people, chooses a csv file and types a first password. Only `username` and
`role` are required columns. The rule is all or nothing: if one line is wrong, no account is created
and every problem is listed with its line number.

Where: `accounts/importer.py` has three functions that run in order. `read_rows` reads the file,
`check_rows` finds every problem, `create_accounts` creates supervisors first and students second,
inside one database transaction. Someone who already has an account is left exactly as they are.

## 3. Passwords

Question it answers: what happens when someone forgets their password, or is handed one?

Everyone can change their password by clicking their name in the header. "Forgot your password?" on
the sign in page emails a link that works once, for three days. Accounts created from a file carry a
mark, `must_change_password`, and `accounts/middleware.py` sends that person to the change password
page before any other page opens. The mark is removed when they choose their own.

The pages themselves are Django's own, tested by thousands of sites. We wrote the templates and two
small classes in `accounts/views.py` that remove the mark.

The answer to an unknown email address is the same as to a known one, so nobody can use the page to
find out who has an account.

## 4. The printable report

Question it answers: what does a supervisor take into a meeting?

"Printable report" on a student's page, and "Print my report" on the student's own timeline. One page:
the score with its reasons, the score over the semester, the ten deliverables, the meetings with their
status, and the feedback. The browser prints it or saves it as PDF, and the print stylesheet hides the
header and the buttons.

Where: `student_report` in `progress/views.py`. The chart is a plain SVG line whose points are worked
out in the view, so it prints the same everywhere and needs no JavaScript. `student_for` is the one
function that decides who may see a student, used by both the student page and the report.

## Tests

72 tests. Seventeen new: five for score settings, four for passwords, five for adding people, three
for the report.
