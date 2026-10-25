# Installable site

The bracket page is a progressive web app. `manifest.webmanifest` names it Payoff Pitch, uses `standalone` display, and points at the icons in `assets/icons/`. `sw.js` caches the shell (the page, the stylesheet, the script, the results file, the team colors, the bios, the odds, and the recap) and falls back to that cache when a request fails. The page registers the worker from `index.html`.

Serve the repository over HTTP, open the site, and use the browser's install control. The first visit registers the worker. The next visit is the one that can open offline. Bump the `CACHE` string in `sw.js` after a shipped asset must replace a cached copy.

Icons are generated marks for this site, not club logos. Club marks are configured in [`data/teams.json`](data/teams.json).

## A future Android wrapper

A Trusted Web Activity can wrap the live site later. It is not set up in this repository.

Joe would:

1. Use Bubblewrap or PWABuilder against `https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/`.
2. Sign the Android package with a key he keeps.
3. Host `/.well-known/assetlinks.json` on that same origin, with the package name and the signing-key fingerprint.
4. Point the activity at the Pages URL. The manifest `start_url` and `scope` are `./`, so they follow the project path.

Until that file and package exist, the install path is the browser, not a store listing.
