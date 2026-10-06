# Walkthrough 2: the pages and who can see them

Written 6 October 2026. Read with walkthrough 1.

## What was added

* A sign in page (`templates/registration/login.html`). Django provides the sign in and sign out logic,
  we only provide the look of the page.
* A home page (`dashboard/views.py`, `home`) that checks your role and sends you to your own page.
* The student timeline (`student_home`): every deliverable with a status badge.
* The supervisor dashboard (`supervisor_home`): one row per student with submitted and missing counts,
  the last meeting and the latest risk status.
* One shared layout (`templates/base.html`) with the navbar, using Bootstrap for the styling.

## How a page works, in one sentence each

1. The browser asks for an address, for example `/student/`.
2. `clptrack/urls.py` and `dashboard/urls.py` match the address to a function in `dashboard/views.py`.
3. The function reads from the database, works things out, and hands the results to a template.
4. The template (an HTML file with placeholders) fills in the results and the browser shows it.

This request, view, template path is the sequence diagram for the thesis.

## Who can see what

`role_required` in `dashboard/views.py` is a small wrapper that checks two things before a page opens:
the person is signed in, and their role is the one the page is for. Anyone else gets a 403, which means
"not allowed". The tests in `dashboard/tests.py` prove it: a student opening `/supervisor/` gets 403, and a
supervisor only sees the students that point at them.

## The timeline statuses

`timeline_for` looks at each deliverable for one student:

| Situation | Status shown |
|---|---|
| A submission exists and it was on time | Submitted |
| A submission exists but it was late | Submitted N days late |
| No submission and the deadline has passed | Missing |
| No submission, deadline within 7 days | Due in N days, shown in amber |
| No submission, deadline further away | Due in N days |

The supervisor dashboard reuses the same function for every student, so the two pages can never disagree.

## A mistake worth remembering

The first version of the "supervisor sees only their own students" test looked for the text "stu" on the
page and failed, because "stu" is inside the word "students" in the heading. Tests should look for
something specific, so it now checks for the student's full name. Small, but it is the kind of thing an
examiner likes to hear: the test was wrong, not the code, and here is how it was found.

## Questions an examiner might ask

* **Why use Django's own sign in instead of writing one?** Passwords, sessions and sign out are easy to
  get wrong and dangerous when wrong. Django's versions are tested by thousands of projects.
* **Where is the check that a student cannot see another student's data?** `role_required` blocks the
  wrong role, and each view only queries the signed in user's own records or their own students.
* **Why Bootstrap?** A ready made set of styles that works on phones, so the time goes into the system
  rather than into CSS.
