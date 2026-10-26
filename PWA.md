# Installable site

The bracket page is a progressive web app. `manifest.webmanifest` names it Payoff Pitch, uses `standalone` display, and points at the icons in `assets/icons/`. `sw.js` caches the shell (the page, the stylesheet, the script, the results file, the team colors, the bios, the announced rosters, the converted roster lists, the odds, and the recap) and falls back to that cache when a request fails. `data/cards.json` and `data/peak162.json` are not in that install cache. The page fetches them when a player card or a Peak 162 line is opened. The page registers the worker from `index.html`.

Serve the repository over HTTP, open the site, and use the browser's install control. The first visit registers the worker. The next visit is the one that can open offline. Bump the `CACHE` string in `sw.js` after a shipped asset must replace a cached copy.

Icons are generated marks for this site, not club logos. Club marks are configured in [`data/teams.json`](data/teams.json).
