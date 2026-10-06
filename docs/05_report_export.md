# Walkthrough 5: the report export

Written 6 October 2026. This is FR11 from the proposal, the "Should" feature.

## What it does

A "Download as spreadsheet" button on the supervisor dashboard and on the coordinator page. It downloads a
csv file named `clptrack_2026-10-06.csv` (today's date) that opens in Excel. One line per student:

| Column | Where it comes from |
|---|---|
| Student ID, Name, Section, Supervisor | the User table |
| Score, Status | the latest RiskScore row, or "not scored" |
| Submitted, Missing, Due so far | the same counts as the dashboard table |
| Last meeting | the most recent Meeting date, or "none" |

A supervisor gets their own students. The coordinator gets everyone. A student who tries the address gets
403, not allowed.

## How it is built (`dashboard/views.py`, `export_csv`)

The dashboard table and the csv were going to need the same numbers, so the code that works them out for
one student was moved into its own small function, `summary_for`. The supervisor page calls it once per
student to build the table, and the export calls it once per student to write a line. One place to fix if
a number is ever wrong.

The export itself is Python's built in `csv` module writing straight into the HTTP response. The
`Content-Disposition: attachment` header is what makes the browser save a file instead of showing text.

## Questions an examiner might ask

* **Why csv and not Excel or PDF?** Csv opens in Excel, Numbers and Google Sheets with nothing to install,
  and it is ten lines of code with no extra library. The supervisor wanted something to sort and filter,
  not a formatted report.
* **Why did you move the counting into `summary_for`?** So the screen and the file can never disagree.
  That is the "do not repeat yourself" rule.
* **How is access controlled?** The view checks the role itself, because two roles may use it. Anyone else
  gets PermissionDenied, and the test `test_student_cannot_download` proves it.

## Tests

Three tests in `dashboard/tests.py`, class `ExportTests`: a supervisor sees only their students and the
file has the right type and headers, the coordinator sees everyone, a student gets 403. Total now 23.
