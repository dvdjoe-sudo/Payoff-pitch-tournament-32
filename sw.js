/* Payoff Pitch offline shell. Bump CACHE when a shipped asset must replace a cached copy. */
var CACHE = "payoff-pitch-v60";
var SHELL = [
  "./",
  "./index.html",
  "./css/styles.css",
  "./js/bracket.js",
  "./manifest.webmanifest",
  "./tournament_results.json",
  "./data/teams.json",
  "./data/team_colors.json",
  "./data/bios.json",
  "./data/announced_rosters.json",
  "./data/rosters.json",
  "./feed/odds.json",
  "./feed/recap.json",
  "./feed/tournament.json",
  "./assets/icons/icon-192.png",
  "./assets/icons/icon-512.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) {
    return cache.addAll(SHELL);
  }));
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (key) { return key !== CACHE; }).map(function (key) {
      return caches.delete(key);
    }));
  }));
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;
  event.respondWith(fetch(request).then(function (response) {
    var copy = response.clone();
    caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
    return response;
  }).catch(function () {
    return caches.match(request).then(function (cached) {
      return cached || caches.match("./index.html");
    });
  }));
});
