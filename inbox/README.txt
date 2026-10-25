Drop a box-score markdown or CSV file in this folder, on main.

The Inbox import workflow reads inbox/*.md and inbox/*.csv, checks the
shape, adds games that are not already stored, validates, regenerates the
pages, commits, and deploys. A file that fails stays here. The reason is
written to inbox/errors/. A file that lands moves to inbox/imported/.

Do not put a changed line for a game that is already on the book in this
folder. The import refuses it. R1-01, R1-02, and R1-03 are locked.

The column layout is in ADDING_GAMES.md. This note is a .txt file so the
workflow does not try to import it.
