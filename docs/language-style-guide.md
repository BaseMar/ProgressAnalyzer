# Language and terminology

English is the project's working language. This applies to the public application,
source code and repository documentation, including historical implementation
records. The goal is a consistent experience for users, contributors and reviewers.

## Writing conventions

- Write README content, technical documentation, comments and docstrings in English.
- Use English names for files, modules, classes, functions, variables and test cases.
- Use English for interface labels, validation messages, tooltips, accessibility
  labels and generated workout notes.
- Write new commit messages and pull request titles and descriptions in English.
- Use sentence case for new labels and headings; preserve existing page names.
- Use decimal points in generated examples and write units explicitly: kg, reps, s.
- Explain abbreviations on first use. RIR means repetitions in reserve.

Comments explain intent, assumptions or constraints. Docstrings describe behavior
and relevant inputs or outputs. Avoid restating code or adding comments solely to
make a function look documented.

## Shared terminology

| Term | Meaning |
| --- | --- |
| Training plan | A versioned weekly routine with prescribed exercises and targets. |
| Scheduled workout | A dated occurrence of a workout in a training plan. |
| Recorded session | A workout saved in the user's history. |
| Working set | A set interpreted or explicitly marked as ordinary working effort. |
| Warm-up set | A set marked or inferred as preparation before working sets. |
| Load | The recorded or suggested weight setting; use weight for an existing field name. |
| Starting load | A load suggested for establishing a baseline in the current context. |
| Baseline | Recorded evidence used to compare performance or determine the next target. |
| Weight increment | The smallest available change in an equipment setting. |
| Load equalization | Increasing lighter sets toward the established first working load. |
| Deload | A scheduled lighter training period under the application's explicit rules. |
| Body mass | The user's measured body mass. |
| Additional load | External weight added to a bodyweight exercise. |
| Assistance | A measured counterweight used for assisted bodyweight work. |
| Target | A suggested result; it is not a performed result. |
| Result | The actual values entered after training. |

Use the existing interface page names: **Overview**, **Analysis**, **Plan** and
**History**. Keep identifiers, database fields and import contracts stable when
editing prose; renaming a technical interface requires its own compatibility review.

## Existing user data and import compatibility

User-entered exercise names, notes and workout names retain their original text.
Translation does not rewrite recorded data or database migrations.

The application generates English workout notes using **Date**, **Workout**,
**Time**, **Target**, **Result** and **RIR**. Targets are ignored during import;
unfilled result and RIR placeholders remain unknown.

The TXT importer also accepts earlier Polish input labels, such as `Godzina`,
`Cel`, `Wynik`, `Rozgrzewka` and `Robocze`. These are compatibility tokens, not
application copy. Tests may contain original-language fixtures to verify that
previously saved notes continue to import correctly.

## Current guidance and historical records

[Progression rules](progression-redesign-rules.md) describe current recommendation
behavior. Dated implementation plans and release reports describe their stated
release; translating them does not turn past test results into current validation.
Retain source links, dates, commit IDs, technical identifiers and historical results.
