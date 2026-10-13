# Walkthrough 11: fixes after a full review

Written 13 October 2026, after reading the whole system the way an examiner would.

## Security

Add people used to give every new account the same first password. With student IDs as usernames, a
student could have signed in as a classmate who had not signed in yet. Now each account gets its own
random first password, shown to the coordinator once. Choosing the same password again is refused, and
a coordinator cannot be created from a file.

## Things that broke on real input

A csv row with one comma too many used to return an error page. The importer now reports the line.
It also checks each row the way Django checks any account: allowed characters, lengths, a real email
address. Usernames are compared without regard to capitals.

One email address that the mail service refused used to stop the daily job for everyone after it.
`_send` now catches the failure, writes it to the log, and moves on. Nothing is written to the
notification log for that person, so it is tried again the next day.

## Speed

Pages that list submissions used to read the bytes of every uploaded file. Every such query now says
`defer("data")`, and only the download view reads the bytes. The site also gives a slow request two
minutes before giving up.

## The score

`save_today` in `risk/scoring.py` works out one student's score and stores it as today's row. The daily
command calls it for everyone, and the pages call it for one student after an upload, a meeting, a
ticked action or a supervisor's decision. Before this the colour only changed the next morning while
the counts beside it changed at once.

The deadline indicator now looks at the nearest deadline the student has not handed anything in for.
Before, uploading for the nearest deadline hid a second one two days later.

A meeting cannot be recorded for a future date, which would have reset the meeting gap.

Dates use the local date in Bahrain. Before, between midnight and three in the morning, the date was
still yesterday's.

## Smaller things

"1 day late" and "Due today" are worded correctly. Badge colours were changed so every badge text has a
contrast of at least 4.5 to 1. The weights can only be changed on their own page, where the rule that
they add up to 100 is checked. The token check is one function.

## Known limits, said plainly

Only missing work can turn a student amber on its own, it is worth 35 and amber starts at 30. A student
who never meets their supervisor but hands everything in on time scores 25 and stays green. The
coordinator can change that on the score settings page, and the preview shows who would be affected.

The cohort page still asks the database several questions per student. It is fine for a class and would
need one query per table at the size of the whole programme.

## Added on 14 October

A file with an Arabic name now downloads with its name, and the type sent to the browser comes from the
file name and not from what was claimed at upload. The database itself now refuses a second row for the
same student and deliverable. A superuser made on the command line is a coordinator, not a student.
Saving new weights sends the alert for any colour that changed. Reminders use wide windows, two to four
days and under two days, so a missed day sends a reminder late and not never.

One more thing the review taught: two of my own tests took the date in UTC. They passed all day and
failed between midnight and three in the morning in Bahrain, when the UTC date is still yesterday. They
now use the local date, the same as the code. 86 tests.
