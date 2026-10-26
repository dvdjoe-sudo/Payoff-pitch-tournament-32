(function () {
  "use strict";

  var STAGES = [
    { title: "Opening round", group: "winners", test: function (id) { return id.indexOf("R1-") === 0; } },
    { title: "Winners round 2", group: "winners", test: function (id) { return id.indexOf("W2-") === 0; } },
    { title: "Winners round 3", group: "winners", test: function (id) { return id.indexOf("W3-") === 0; } },
    { title: "Winners round 4", group: "winners", test: function (id) { return id.indexOf("W4-") === 0; } },
    { title: "Winners final", group: "winners", test: function (id) { return id.indexOf("W5-") === 0; } },
    { title: "Losers round 1", group: "losers", test: function (id) { return id.indexOf("L1-") === 0; } },
    { title: "Losers round 2", group: "losers", test: function (id) { return id.indexOf("L2-") === 0; } },
    { title: "Losers round 3", group: "losers", test: function (id) { return id.indexOf("L3-") === 0; } },
    { title: "Losers round 4", group: "losers", test: function (id) { return id.indexOf("L4-") === 0; } },
    { title: "Losers round 5", group: "losers", test: function (id) { return id.indexOf("L5-") === 0; } },
    { title: "Losers round 6", group: "losers", test: function (id) { return id.indexOf("L6-") === 0; } },
    { title: "Losers round 7", group: "losers", test: function (id) { return id.indexOf("L7-") === 0; } },
    { title: "Losers final", group: "losers", test: function (id) { return id.indexOf("L8-") === 0; } },
    { title: "Championship", group: "finals", test: function (id) { return id.indexOf("F-") === 0; } }
  ];

  var GROUPS = [
    { id: "winners", title: "Winners bracket", blurb: "The opening round is the first winners stage. Later winners stages reseed when they form." },
    { id: "losers", title: "Losers bracket", blurb: "A club enters here with one series loss. The next series loss eliminates it." },
    { id: "finals", title: "Finals", blurb: "F-02 is stored as its own slot. Its gate says when it is played." }
  ];

  var STATUS = {
    complete: "Final",
    scheduled: "Scheduled",
    "awaiting-feeders": "Waiting",
    "in-progress": "In progress"
  };

  // Display models from MODELS.md. 0.55 is the higher seed's chance in a remaining game.
  // 1.35 is the win-probability scale on margin / sqrt(innings left).
  var HIGHER_SEED_P = 0.55;
  var WP_SCALE = 1.35;

  var state = {
    data: null, byCode: {}, games: {}, players: {}, highlight: "",
    colors: {}, bios: {}, odds: null, recap: null, plays: null,
    cards: {}, rosters: {}, announced: {}, peak: null
  };
  var detailCache = {};
  var renderToken = 0;

  var view = document.getElementById("view");
  var lede = document.getElementById("lede");
  var footer = document.getElementById("footer-note");
  var errorBox = document.getElementById("load-error");
  var nextUp = document.getElementById("next-up");
  var searchForm = document.getElementById("search-form");
  var searchInput = document.getElementById("search");
  var themeButton = document.getElementById("theme-toggle");
  var menuButton = document.getElementById("menu-toggle");
  var siteHeader = document.getElementById("site-header");
  var banner = document.getElementById("milestone-banner");

  function el(tag, attrs) {
    var node = document.createElement(tag);
    var children = Array.prototype.slice.call(arguments, 2);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        var value = attrs[key];
        if (value == null || value === false) return;
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else node.setAttribute(key, value === true ? "" : value);
      });
    }
    children.forEach(function (child) {
      if (child == null || child === false) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  function svg(name, attrs) {
    var node = document.createElementNS("http://www.w3.org/2000/svg", name);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        node.setAttribute(key, attrs[key]);
      });
    }
    return node;
  }

  function nz(value) {
    return value || 0;
  }

  function ipLabel(outs) {
    return Math.floor(outs / 3) + "." + (outs % 3);
  }

  function rateLabel(numer, denom) {
    if (!denom) return "—";
    var average = numer / denom;
    if (average >= 1) return "1.000";
    return average.toFixed(3).replace(/^0/, "");
  }

  function eraLabel(er, outs) {
    if (!outs) return "—";
    return ((27 * er) / outs).toFixed(2);
  }

  function q1(value) {
    return (Math.round(value * 10) / 10).toFixed(1);
  }

  function clubName(code) {
    if (!code) return "TBD";
    var team = state.byCode[code];
    return team ? team.name : code;
  }

  function placeholderColor(seed) {
    var hue = (Number(seed) * 47) % 360;
    return "hsl(" + hue + ", 46%, 36%)";
  }

  function teamColors(code) {
    return (state.colors && code && state.colors[code]) || null;
  }

  function logo(team, label) {
    var colors = team ? teamColors(team.code) : null;
    var alt = label || (team && team.name ? team.name + " mark" : "Club mark");
    if (colors && colors.logo) {
      return el("img", { class: "logo", src: colors.logo, alt: alt, width: "64", height: "64" });
    }
    var color = colors && colors.primary ? colors.primary : placeholderColor(team ? team.seed : 1);
    var ink = colors && colors.font ? colors.font : "#f6f1e6";
    var node = svg("svg", { class: "logo", viewBox: "0 0 64 64", role: "img" });
    node.appendChild(svg("title")).textContent = alt;
    node.appendChild(svg("rect", { width: "64", height: "64", rx: "8", fill: color }));
    var text = svg("text", {
      x: "32", y: "40", "text-anchor": "middle",
      "font-family": "Georgia, serif", "font-size": "18", fill: ink
    });
    text.textContent = team ? team.code : "";
    node.appendChild(text);
    return node;
  }

  function showError(message) {
    errorBox.hidden = false;
    errorBox.textContent = message;
    lede.textContent = "The bracket could not be loaded.";
  }

  function storageGet(key) {
    try { return localStorage.getItem(key) || ""; } catch (err) { return ""; }
  }

  function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch (err) { /* ignore */ }
  }

  function route() {
    var raw = (location.hash || "#/bracket").replace(/^#/, "");
    var query = "";
    var qIndex = raw.indexOf("?");
    if (qIndex !== -1) {
      var params = new URLSearchParams(raw.slice(qIndex + 1));
      query = params.get("q") || "";
      raw = raw.slice(0, qIndex);
    }
    var parts = raw.split("/").filter(Boolean);
    if (!parts.length) parts = ["bracket"];
    return { name: parts[0], rest: parts.slice(1).map(decodeURIComponent), query: query };
  }

  function markNav(name) {
    document.querySelectorAll(".views a").forEach(function (link) {
      var on = link.getAttribute("data-view") === name;
      if (on) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function table(headers, rows) {
    var wrap = el("div", { class: "table-wrap" });
    var t = el("table");
    var head = el("tr");
    headers.forEach(function (header, index) {
      head.appendChild(el("th", { text: header, class: index === 0 ? null : "num" }));
    });
    t.appendChild(el("thead", null, head));
    var body = el("tbody");
    rows.forEach(function (row) {
      var tr = el("tr");
      row.forEach(function (cell, index) {
        var td = el("td", { class: index === 0 ? null : "num" });
        if (cell && cell.nodeType) td.appendChild(cell);
        else td.textContent = cell == null ? "" : String(cell);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    t.appendChild(body);
    wrap.appendChild(t);
    return wrap;
  }

  function linkPlayer(code, id, name) {
    return el("a", { class: "player-link", href: "#/player/" + code + "/" + encodeURIComponent(id), text: name });
  }

  function linkTeam(code, name) {
    return el("a", { class: "team-link", href: "#/team/" + code, text: name || clubName(code) });
  }

  function linkGame(id, label) {
    return el("a", { href: "#/game/" + id, text: label || id });
  }

  function seriesWinProb(winsFor, winsAgainst) {
    var memo = {};
    function walk(left, opp) {
      var key = left + "," + opp;
      if (memo[key] != null) return memo[key];
      var value;
      if (left <= 0) value = 1;
      else if (opp <= 0) value = 0;
      else value = HIGHER_SEED_P * walk(left - 1, opp) + (1 - HIGHER_SEED_P) * walk(left, opp - 1);
      memo[key] = value;
      return value;
    }
    return walk(4 - winsFor, 4 - winsAgainst);
  }

  function higherSeed(series) {
    if (series.seed_a == null || series.seed_b == null || !series.team_a || !series.team_b) return null;
    return series.seed_a <= series.seed_b ? series.team_a : series.team_b;
  }

  function mcOdds(series) {
    var table = state.odds && state.odds.series && state.odds.series[series.id];
    if (!table || !series.team_a || !series.team_b) return null;
    if (table[series.team_a] == null || table[series.team_b] == null) return null;
    return {
      a: series.team_a,
      b: series.team_b,
      pA: Number(table[series.team_a]),
      pB: Number(table[series.team_b]),
      source: "monte-carlo"
    };
  }

  function oddsFor(series) {
    var mc = mcOdds(series);
    if (mc) return mc;
    if (!series.team_a || !series.team_b) return null;
    var high = higherSeed(series);
    if (!high) return null;
    var low = high === series.team_a ? series.team_b : series.team_a;
    var wins = series.wins || {};
    var pHigh;
    if (series.status === "complete" && series.winner) {
      pHigh = series.winner === high ? 1 : 0;
    } else {
      pHigh = seriesWinProb(nz(wins[high]), nz(wins[low]));
    }
    return { a: high, b: low, pA: pHigh, pB: 1 - pHigh, source: "seed" };
  }

  function percent(value) {
    return (Math.round(Number(value) * 1000) / 10).toFixed(1);
  }

  function oddsBar(series) {
    var odds = oddsFor(series);
    if (!odds) return null;
    var left = percent(odds.pA);
    var right = percent(odds.pB);
    var track = el("div", { class: "odds-track" });
    var a = el("span", { text: left + "%" });
    var b = el("span", { text: right + "%" });
    a.style.width = left + "%";
    b.style.width = right + "%";
    var colorA = teamColors(odds.a);
    var colorB = teamColors(odds.b);
    a.style.background = colorA && colorA.primary ? colorA.primary : placeholderColor(state.byCode[odds.a] ? state.byCode[odds.a].seed : 1);
    b.style.background = colorB && colorB.primary ? colorB.primary : placeholderColor(state.byCode[odds.b] ? state.byCode[odds.b].seed : 2);
    if (colorA && colorA.font) a.style.color = colorA.font;
    if (colorB && colorB.font) b.style.color = colorB.font;
    track.appendChild(a);
    track.appendChild(b);
    var note = odds.source === "monte-carlo"
      ? "Series odds from the Monte Carlo in MODELS.md. A finished series is the recorded result. A shown 0.0% means that side won none of the 4,000 draws."
      : "Series odds, higher seed " + HIGHER_SEED_P + " each remaining game. A finished series shows the winner at 100%.";
    return el("div", { class: "odds" },
      el("p", { class: "muted", text: note }),
      el("p", null, linkTeam(odds.a), " " + left + "% · ", linkTeam(odds.b), " " + right + "%"),
      track
    );
  }

  function homeWp(margin, inning, bottom) {
    var inningsLeft = Math.max(0.5, 9.5 - inning - (bottom ? 0.5 : 0));
    var scale = WP_SCALE / Math.sqrt(inningsLeft);
    return 1 / (1 + Math.exp(-scale * margin));
  }

  function halfText(game, inning, bottom, runs, home, away) {
    var word = runs === 1 ? "run" : "runs";
    return (bottom ? "Bottom " : "Top ") + inning + ": " + runs + " " + word + " on the line score. " +
      clubName(game.away) + " " + away + ", " + clubName(game.home) + " " + home + ".";
  }

  function lineHalves(game) {
    var awayLine = game.line && game.line[game.away];
    var homeLine = game.line && game.line[game.home];
    if (!Array.isArray(awayLine) || !Array.isArray(homeLine)) return null;
    if (!awayLine.length && !homeLine.length) return null;
    var n = Math.max(awayLine.length, homeLine.length);
    var home = 0;
    var away = 0;
    var events = [];
    var i;
    for (i = 0; i < n; i++) {
      if (i < awayLine.length) {
        if (typeof awayLine[i] !== "number") return null;
        away += awayLine[i];
        events.push({
          inning: i + 1, bottom: false, home: home, away: away, runs: awayLine[i],
          text: halfText(game, i + 1, false, awayLine[i], home, away)
        });
      }
      if (i < homeLine.length) {
        if (typeof homeLine[i] !== "number") return null;
        home += homeLine[i];
        events.push({
          inning: i + 1, bottom: true, home: home, away: away, runs: homeLine[i],
          text: halfText(game, i + 1, true, homeLine[i], home, away)
        });
      }
    }
    if (home !== game.score[game.home] || away !== game.score[game.away]) return null;
    return events;
  }

  function acceptPlays(game, events) {
    var home = 0;
    var away = 0;
    var out = [];
    var i;
    for (i = 0; i < events.length; i++) {
      var item = events[i];
      if (item.home < home || item.away < away) return null;
      if (item.home === home && item.away === away) return null;
      if (item.home > home && item.away > away) return null;
      out.push({
        inning: item.inning,
        bottom: item.home > home,
        home: item.home,
        away: item.away,
        text: item.text
      });
      home = item.home;
      away = item.away;
    }
    if (home !== game.score[game.home] || away !== game.score[game.away]) return null;
    return out;
  }

  function scoringEvents(game) {
    var plays = game.scoring_plays || [];
    if (!plays.length) return null;
    var coded = [];
    var tails = [];
    var i;
    for (i = 0; i < plays.length; i++) {
      var text = String(plays[i] || "");
      var inningMatch = /Inning\s+(\d+)/.exec(text);
      if (!inningMatch) return null;
      var inning = parseInt(inningMatch[1], 10);
      var pair = /([A-Z]{2,3})\s+(\d+),\s*([A-Z]{2,3})\s+(\d+)/.exec(text);
      if (pair) {
        var map = {};
        map[pair[1]] = Number(pair[2]);
        map[pair[3]] = Number(pair[4]);
        if (map[game.home] == null || map[game.away] == null) return null;
        coded.push({ inning: inning, home: map[game.home], away: map[game.away], text: text });
      } else {
        var tail = /(\d+)\s*-\s*(\d+)\s*$/.exec(text);
        if (!tail) return null;
        tails.push({ inning: inning, a: Number(tail[1]), b: Number(tail[2]), text: text });
      }
    }
    if (coded.length && tails.length) return null;
    if (coded.length) return acceptPlays(game, coded);
    var asHome = tails.map(function (item) {
      return { inning: item.inning, home: item.a, away: item.b, text: item.text };
    });
    var asAway = tails.map(function (item) {
      return { inning: item.inning, home: item.b, away: item.a, text: item.text };
    });
    return acceptPlays(game, asHome) || acceptPlays(game, asAway);
  }

  function chartEvents(game) {
    var halves = lineHalves(game);
    if (!halves) return null;
    var plays = scoringEvents(game);
    if (!plays) return { events: halves, source: "line" };
    var merged = [];
    var index = 0;
    var h;
    for (h = 0; h < halves.length; h++) {
      var half = halves[h];
      var batch = [];
      while (index < plays.length && plays[index].inning === half.inning && plays[index].bottom === half.bottom) {
        batch.push(plays[index]);
        index += 1;
      }
      if (half.runs > 0) {
        var last = batch[batch.length - 1];
        if (!last || last.home !== half.home || last.away !== half.away) return { events: halves, source: "line" };
        batch.forEach(function (play) { merged.push(play); });
      } else if (batch.length) {
        return { events: halves, source: "line" };
      } else {
        merged.push(half);
      }
    }
    if (index !== plays.length) return { events: halves, source: "line" };
    return { events: merged, source: "plays" };
  }

  function wpChart(game) {
    var built = chartEvents(game);
    if (!built) return null;
    var points = [{ label: "Start", p: 0.5, text: "Before the first pitch. The model starts the home club at 50%." }];
    built.events.forEach(function (event) {
      points.push({
        label: (event.bottom ? "Bot " : "Top ") + event.inning,
        p: homeWp(event.home - event.away, event.inning, event.bottom),
        text: event.text
      });
    });
    var width = 640;
    var height = 220;
    var padL = 44;
    var padR = 16;
    var padY = 22;
    var chart = svg("svg", { class: "chart", viewBox: "0 0 " + width + " " + height, role: "img" });
    chart.appendChild(svg("title")).textContent = "Model estimate of " + clubName(game.home) + " win probability";
    function axisLabel(x, y, text, anchor) {
      var node = svg("text", { x: String(x), y: String(y), fill: "currentColor", "text-anchor": anchor || "end", "font-size": "12" });
      node.textContent = text;
      chart.appendChild(node);
    }
    axisLabel(padL - 6, padY + 4, "100%");
    axisLabel(padL - 6, padY + (height - 2 * padY) / 2 + 4, "50%");
    axisLabel(padL - 6, height - padY + 4, "0%");
    chart.appendChild(svg("line", { x1: padL, y1: padY, x2: padL, y2: height - padY, stroke: "#8a8175" }));
    chart.appendChild(svg("line", { x1: padL, y1: height - padY, x2: width - padR, y2: height - padY, stroke: "#8a8175" }));
    chart.appendChild(svg("line", {
      x1: padL, y1: padY + (height - 2 * padY) / 2,
      x2: width - padR, y2: padY + (height - 2 * padY) / 2,
      stroke: "#c6a15a", "stroke-dasharray": "4 4"
    }));
    var coords = points.map(function (point, index) {
      var x = padL + (points.length === 1 ? 0 : (index / (points.length - 1)) * (width - padL - padR));
      var y = padY + (1 - point.p) * (height - 2 * padY);
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    chart.appendChild(svg("polyline", { points: coords, fill: "none", stroke: "#1d5c3d", "stroke-width": "2" }));
    var how = built.source === "plays"
      ? "Steps are the stored scoring plays. A half-inning with no runs stays one line-score step."
      : "Each step is one half-inning from the line score. A multi-run half stays one step, because the file does not say which run scored first.";
    var caption = "Model estimate for the home club, " + clubName(game.home) + ". The formula in MODELS.md uses the inning, the half, and the run margin. " + how + " This is not a recorded win probability.";
    var list = el("ol", { class: "muted" });
    points.forEach(function (point) {
      list.appendChild(el("li", { text: point.label + ": home " + Math.round(point.p * 100) + "%. " + point.text }));
    });
    return el("div", { class: "wp-chart no-print" },
      el("h4", { text: "Win probability (model estimate)" }),
      chart,
      el("p", { class: "muted", text: caption }),
      el("details", null, el("summary", { text: "Model estimate after each step" }), list)
    );
  }

  function nextGame() {
    var found = null;
    state.data.series.forEach(function (series) {
      if (found || series.status !== "in-progress") return;
      var number = (series.games || []).length + 1;
      var home = (series.home_by_game || {})[String(number)];
      if (!home || !series.team_a) return;
      var away = home === series.team_a ? series.team_b : series.team_a;
      var starters = (series.carry && series.carry.rotation_next_start) || {};
      found = { series: series, number: number, home: home, away: away, starters: starters };
    });
    if (found) return found;
    state.data.series.forEach(function (series) {
      if (found || series.status !== "scheduled" || !series.team_a || !series.team_b) return;
      var home = (series.home_by_game || {})["1"];
      if (!home) return;
      var away = home === series.team_a ? series.team_b : series.team_a;
      found = { series: series, number: 1, home: home, away: away, starters: {} };
    });
    return found;
  }

  function renderNext() {
    clear(nextUp);
    var upcoming = nextGame();
    if (!upcoming) {
      nextUp.appendChild(el("p", { class: "next-line", text: "No series is in progress." }));
      return;
    }
    var homeStarter = upcoming.starters[upcoming.home] || "starter not named";
    var awayStarter = upcoming.starters[upcoming.away] || "starter not named";
    var line = el("div", { class: "next-line" });
    line.appendChild(el("span", { class: "eyebrow", text: "Next" }));
    line.appendChild(el("a", {
      href: "#/series/" + upcoming.series.id,
      text: upcoming.series.id + " Game " + upcoming.number + " at " + clubName(upcoming.home)
    }));
    var toggle = el("button", { type: "button", class: "next-toggle", "aria-expanded": "false", text: "Starters" });
    line.appendChild(toggle);
    nextUp.appendChild(line);
    nextUp.appendChild(el("p", {
      class: "next-detail",
      text: awayStarter + " (" + upcoming.away + ") at " + homeStarter + " (" + upcoming.home + ")."
    }));
    toggle.addEventListener("click", function () {
      var open = nextUp.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function paOf(stats) {
    return stats.ab + stats.bb + stats.hbp + stats.sac + stats.sf;
  }

  function totalBases(stats) {
    return stats.h + stats.doubles + (2 * stats.triples) + (3 * stats.hr);
  }

  function indexPlayers() {
    var players = {};
    function bucket(code, id, name) {
      var key = code + "|" + id;
      if (!players[key]) {
        players[key] = {
          key: key, team: code, id: id, name: name,
          bat: { ab: 0, r: 0, h: 0, rbi: 0, bb: 0, k: 0, hbp: 0, sb: 0, cs: 0, sac: 0, sf: 0, doubles: 0, triples: 0, hr: 0 },
          pit: { outs: 0, h: 0, r: 0, er: 0, bb: 0, k: 0, hr: 0, gs: 0, w: 0, l: 0, sv: 0 },
          log: [], grades: []
        };
      }
      players[key].name = name;
      return players[key];
    }
    state.data.games.forEach(function (game) {
      game.batting.forEach(function (line) {
        var player = bucket(line.team, line.player_id, line.name);
        ["ab", "r", "h", "rbi", "bb", "k", "hbp", "sb", "cs", "sac", "sf", "doubles", "triples", "hr"].forEach(function (field) {
          player.bat[field] += nz(line[field]);
        });
        player.log.push({ game: game.id, side: "bat", line: line });
      });
      game.pitching.forEach(function (line) {
        var player = bucket(line.team, line.player_id, line.name);
        ["outs", "h", "r", "er", "bb", "k", "hr"].forEach(function (field) {
          player.pit[field] += nz(line[field]);
        });
        if (line.appearance_order === 1) player.pit.gs += 1;
        player.log.push({ game: game.id, side: "pit", line: line });
      });
      ["W", "L", "S"].forEach(function (decision) {
        var award = game.wls && game.wls[decision];
        if (!award) return;
        var player = bucket(award.team, award.player_id, award.name);
        player.pit[decision === "S" ? "sv" : decision.toLowerCase()] += 1;
      });
      var grades = game.final_grades || {};
      Object.keys(grades).forEach(function (key) {
        if (!players[key]) return;
        players[key].grades.push({ game: game.id, grade: grades[key] });
      });
    });
    state.players = players;
  }

  function runDiff() {
    var table = {};
    state.data.teams.forEach(function (team) {
      table[team.code] = { rs: 0, ra: 0 };
    });
    state.data.games.forEach(function (game) {
      table[game.home].rs += game.score[game.home];
      table[game.home].ra += game.score[game.away];
      table[game.away].rs += game.score[game.away];
      table[game.away].ra += game.score[game.home];
    });
    return table;
  }

  function awards() {
    var mvp = [];
    var cy = [];
    var rel = [];
    Object.keys(state.players).forEach(function (key) {
      var player = state.players[key];
      var bat = player.bat;
      if (paOf(bat) > 0) {
        var points = totalBases(bat) + bat.r + bat.rbi + bat.sb - bat.cs + (0.5 * bat.bb) + (0.5 * bat.hbp);
        mvp.push({ player: player, points: points });
      }
      var pit = player.pit;
      if (pit.outs + pit.w + pit.sv === 0) return;
      var ip = pit.outs / 3;
      if (pit.gs >= 1) {
        cy.push({ player: player, points: ip + (0.4 * pit.k) + (5 * pit.w) - (1.5 * pit.er) - (0.3 * pit.bb) });
      } else {
        rel.push({ player: player, points: (5 * pit.sv) + (2 * ip) + (0.4 * pit.k) - (1.5 * pit.er) });
      }
    });
    function byPoints(a, b) { return b.points - a.points || a.player.name.localeCompare(b.player.name); }
    mvp.sort(byPoints);
    cy.sort(byPoints);
    rel.sort(byPoints);
    return { mvp: mvp, cy: cy, rel: rel };
  }

  function milestones() {
    var nohitters = [];
    var highK = [];
    var big = [];
    state.data.games.forEach(function (game) {
      game.pitching.forEach(function (line) {
        if (line.appearance_order === 1 && nz(line.h) === 0 && nz(line.outs) >= 27) {
          nohitters.push({ game: game, line: line });
        }
        if (nz(line.k) >= 10) highK.push({ game: game, line: line });
      });
      [game.home, game.away].forEach(function (code) {
        if (game.score[code] >= 10) big.push({ game: game, code: code });
      });
    });
    highK.sort(function (a, b) { return nz(b.line.k) - nz(a.line.k); });
    return { nohitters: nohitters, highK: highK, big: big };
  }

  function seriesCard(series, activeId) {
    var classes = "series-card";
    if (series.id === activeId) classes += " selected";
    if (state.highlight && (series.team_a === state.highlight || series.team_b === state.highlight)) classes += " on-path";
    var card = el("a", { class: classes, href: "#/series/" + series.id });
    card.appendChild(el("div", { class: "series-id" },
      el("span", { text: series.id }),
      el("span", { text: STATUS[series.status] || series.status })
    ));
    [series.team_a, series.team_b].forEach(function (code) {
      if (!code && series.status === "awaiting-feeders") {
        card.appendChild(el("div", { class: "club-line" }, el("span", { text: "TBD" }), el("span", { class: "runs", text: "" })));
        return;
      }
      var wins = series.wins && code && Object.prototype.hasOwnProperty.call(series.wins, code) ? String(series.wins[code]) : "";
      var name = (code && series.seed_a != null && code === series.team_a ? "#" + series.seed_a + " " : "");
      if (code && code === series.team_b && series.seed_b != null) name = "#" + series.seed_b + " ";
      name += clubName(code);
      var rowClass = "club-line" + (series.winner && series.winner === code ? " winner-club" : "");
      card.appendChild(el("div", { class: rowClass },
        el("span", { text: name }),
        el("span", { class: "runs", text: wins })
      ));
    });
    var mc = mcOdds(series);
    if (mc) {
      card.appendChild(el("p", {
        class: "card-odds",
        text: series.team_a + " " + percent(mc.pA) + "% · " + series.team_b + " " + percent(mc.pB) + "%"
      }));
    }
    return card;
  }

  function twoDigits(value) {
    return (value < 10 ? "0" : "") + value;
  }

  function recordedMoments() {
    var moments = [];
    var found = milestones();
    found.nohitters.forEach(function (item) {
      moments.push({
        key: item.game.id + "\t0\t" + item.line.name,
        title: item.line.name + " no-hitter",
        text: ipLabel(nz(item.line.outs)) + " IP, 0 H, " + nz(item.line.k) + " K in " + item.game.id + ".",
        href: "#/game/" + item.game.id,
        when: item.game.date || ""
      });
    });
    found.highK.forEach(function (item) {
      moments.push({
        key: item.game.id + "\t1\t" + item.line.player_id,
        title: item.line.name + ", " + nz(item.line.k) + " strikeouts",
        text: nz(item.line.k) + " K in " + ipLabel(nz(item.line.outs)) + " IP, " + item.game.id + ".",
        href: "#/game/" + item.game.id,
        when: item.game.date || ""
      });
    });
    state.data.games.forEach(function (game) {
      if (!isWalkOff(game)) return;
      var series = state.data.series.filter(function (item) { return item.id === game.series_id; })[0];
      var narrative = "";
      if (series && series.narratives) {
        series.narratives.forEach(function (item) {
          if (item.game === game.id && /walk-off/i.test(item.text || "")) narrative = item.text;
        });
      }
      moments.push({
        key: game.id + "\t2\twalk-off",
        title: clubName(game.home) + " walk-off",
        text: narrative || (clubName(game.home) + " won " + game.score[game.home] + "-" + game.score[game.away] + " on a walk-off in " + game.id + "."),
        href: "#/game/" + game.id,
        when: game.date || ""
      });
    });
    found.big.forEach(function (item) {
      var opponent = item.game.home === item.code ? item.game.away : item.game.home;
      moments.push({
        key: item.game.id + "\t3\t" + item.code,
        title: clubName(item.code) + " scored " + item.game.score[item.code],
        text: clubName(item.code) + " scored " + item.game.score[item.code] + " against " + clubName(opponent) + " in " + item.game.id + ".",
        href: "#/game/" + item.game.id,
        when: item.game.date || ""
      });
    });
    state.data.series.forEach(function (series) {
      if (series.status !== "complete" || !series.winner || !series.loser) return;
      var dates = (series.games || []).map(function (id) { return state.games[id] && state.games[id].date; }).filter(Boolean).sort();
      moments.push({
        key: series.id + "\t4\tfinal",
        title: series.id + " final",
        text: clubName(series.winner) + " beat " + clubName(series.loser) + " " + series.wins[series.winner] + "-" + series.wins[series.loser] + (series.mvp && series.mvp.name ? ". MVP " + series.mvp.name + "." : "."),
        href: "#/series/" + series.id,
        when: dates.length ? dates[dates.length - 1] : ""
      });
    });
    moments.sort(function (a, b) {
      if (a.key < b.key) return -1;
      if (a.key > b.key) return 1;
      return 0;
    });
    return moments;
  }

  function onThisDayCard() {
    var moments = recordedMoments();
    if (!moments.length) return null;
    var now = new Date();
    var day = Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000);
    var index = ((day % moments.length) + moments.length) % moments.length;
    var item = moments[index];
    var iso = now.getFullYear() + "-" + twoDigits(now.getMonth() + 1) + "-" + twoDigits(now.getDate());
    return el("section", { class: "on-this-day" },
      el("h2", { text: "On this day" }),
      el("p", { class: "meta", text: iso + " · recorded moment " + (index + 1) + " of " + moments.length }),
      el("p", null, el("a", { href: item.href, text: item.title })),
      el("p", { text: item.text }),
      el("p", { class: "muted", text: "Game date " + (item.when || "not stored") + ". The same calendar date always shows this recorded moment. The card does not add a result." })
    );
  }

  function renderBracket(activeId) {
    markNav("bracket");
    var root = el("div");
    var today = onThisDayCard();
    if (today) root.appendChild(today);
    var select = el("select", { id: "path-select" });
    select.appendChild(el("option", { value: "", text: "All clubs" }));
    state.data.teams.slice().sort(function (a, b) { return a.seed - b.seed; }).forEach(function (team) {
      var option = el("option", { value: team.code, text: "#" + team.seed + " " + team.name });
      if (team.code === state.highlight) option.setAttribute("selected", "");
      select.appendChild(option);
    });
    select.addEventListener("change", function () {
      state.highlight = select.value;
      storageSet("pp-path", state.highlight);
      render();
    });
    root.appendChild(el("div", { class: "path-row" },
      el("label", { for: "path-select", text: "Highlight a club's path" }),
      select
    ));
    root.appendChild(el("p", { class: "note", text: "Swipe the rounds sideways. A series score is the games each club has won. Click a series for its games." }));
    var strip = titleStrip();
    if (strip) root.appendChild(strip);
    GROUPS.forEach(function (group) {
      var block = el("section", { class: "group " + group.id });
      block.appendChild(el("h2", { text: group.title }));
      block.appendChild(el("p", { class: "note", text: group.blurb }));
      var scroller = el("div", { class: "scroller" });
      STAGES.filter(function (stage) { return stage.group === group.id; }).forEach(function (stage) {
        var column = el("div", { class: "round" });
        column.appendChild(el("h3", { text: stage.title }));
        state.data.series.filter(function (series) { return stage.test(series.id); })
          .sort(function (a, b) { return a.id.localeCompare(b.id); })
          .forEach(function (series) { column.appendChild(seriesCard(series, activeId)); });
        scroller.appendChild(column);
      });
      block.appendChild(scroller);
      root.appendChild(block);
    });
    clear(view);
    view.appendChild(root);
  }

  function narrativeFor(gameId) {
    var text = "";
    state.data.series.forEach(function (series) {
      (series.narratives || []).forEach(function (item) {
        if (item.game === gameId) text = item.text;
      });
    });
    return text;
  }

  function seriesCounting(series) {
    if (!series.team_a || !series.team_b || !(series.games || []).length) return null;
    var totals = {};
    totals[series.team_a] = { r: 0, h: 0, hr: 0 };
    totals[series.team_b] = { r: 0, h: 0, hr: 0 };
    var any = false;
    (series.games || []).forEach(function (id) {
      var game = state.games[id];
      if (!game) return;
      any = true;
      [game.away, game.home].forEach(function (code) {
        if (!totals[code]) return;
        totals[code].r += game.score[code];
        game.batting.forEach(function (line) {
          if (line.team !== code) return;
          totals[code].h += nz(line.h);
          totals[code].hr += nz(line.hr);
        });
      });
    });
    if (!any) return null;
    return el("p", {
      text: clubName(series.team_a) + " " + totals[series.team_a].r + " runs, " + totals[series.team_a].h + " hits, " + totals[series.team_a].hr + " home runs. " + clubName(series.team_b) + " " + totals[series.team_b].r + " runs, " + totals[series.team_b].h + " hits, " + totals[series.team_b].hr + " home runs."
    });
  }

  function renderSeries(id) {
    markNav("bracket");
    var series = state.data.series.filter(function (item) { return item.id === id; })[0];
    clear(view);
    if (!series) {
      view.appendChild(el("p", { text: "That series is not in the archive." }));
      return;
    }
    var page = el("article", { class: "panel" });
    page.appendChild(el("p", null, el("a", { href: "#/bracket", text: "Back to the bracket" })));
    page.appendChild(el("h2", { text: series.label || series.id }));
    page.appendChild(el("p", { class: "meta", text: (STATUS[series.status] || series.status) + " · " + series.id }));
    if (series.team_a) {
      page.appendChild(el("p", null, linkTeam(series.team_a), " vs ", linkTeam(series.team_b)));
    }
    page.appendChild(oddsBar(series));
    if (series.mvp) {
      page.appendChild(el("h3", { text: "Series MVP" }));
      page.appendChild(el("p", null,
        linkPlayer(series.mvp.team, series.mvp.player_id, series.mvp.name),
        " · " + series.mvp.line
      ));
      if (series.mvp_runner_up) {
        page.appendChild(el("p", null,
          "Runner-up: ",
          linkPlayer(series.mvp_runner_up.team, series.mvp_runner_up.player_id, series.mvp_runner_up.name),
          " · " + series.mvp_runner_up.line
        ));
      }
    }
    var counted = seriesCounting(series);
    if (counted) page.appendChild(counted);
    var games = el("div", { class: "stack" });
    (series.games || []).forEach(function (gameId) {
      var game = state.games[gameId];
      if (!game) return;
      games.appendChild(el("p", null,
        linkGame(game.id, "Game " + game.game_in_series),
        " ",
        clubName(game.away) + " " + game.score[game.away] + ", " + clubName(game.home) + " " + game.score[game.home]
      ));
    });
    if (!(series.games || []).length) page.appendChild(el("p", { text: "No games have been played in this series." }));
    page.appendChild(games);
    if (series.narratives && series.narratives.length) {
      page.appendChild(el("h3", { text: "How the series turned" }));
      series.narratives.forEach(function (item) {
        page.appendChild(el("p", null, linkGame(item.game, item.game), " ", item.text));
      });
    }
    var graphic = "graphics/series/" + series.id + ".svg";
    if (series.status === "complete" || series.status === "in-progress") {
      var img = el("img", { class: "share-card", src: graphic, alt: series.id + " series score graphic" });
      page.appendChild(el("h4", { text: "Share" }));
      page.appendChild(el("p", null, img));
      page.appendChild(el("p", null,
        el("a", { href: graphic, text: "SVG" }),
        " · ",
        el("a", { href: "graphics/series/" + series.id + ".png", text: "PNG" }),
        " · ",
        el("a", { href: "share/" + series.id + ".html", text: "Share page" })
      ));
    } else if (series.team_a && series.team_b) {
      page.appendChild(el("p", null, el("a", { href: "share/" + series.id + ".html", text: "Share page" })));
    }
    view.appendChild(page);
  }

  function linescore(game) {
    var away = game.away;
    var home = game.home;
    var n = Math.max((game.line[away] || []).length, (game.line[home] || []).length, 9);
    var headers = ["Team"];
    var i;
    for (i = 1; i <= n; i++) headers.push(String(i));
    headers.push("R", "H", "E");
    function row(code) {
      var cells = [clubName(code)];
      var inn = game.line[code] || [];
      for (i = 0; i < n; i++) {
        if (i < inn.length) cells.push(String(inn[i]));
        else cells.push(code === home ? "x" : "");
      }
      var hits = game.batting.filter(function (line) { return line.team === code; })
        .reduce(function (sum, line) { return sum + nz(line.h); }, 0);
      cells.push(String(game.score[code]), String(hits), String((game.team_errors || {})[code] || 0));
      return cells;
    }
    return table(headers, [row(away), row(home)]);
  }

  function decisionText(game) {
    var parts = [];
    [["W", "W"], ["L", "L"], ["S", "S"]].forEach(function (pair) {
      var award = game.wls && game.wls[pair[0]];
      if (award) parts.push(pair[1] + " " + award.name);
    });
    return parts.join(" · ") || "No decision recorded";
  }

  function boxTables(game) {
    var wrap = el("div");
    [game.away, game.home].forEach(function (code) {
      wrap.appendChild(el("h4", { text: clubName(code) + " batting" }));
      var lines = game.batting.filter(function (line) { return line.team === code; })
        .sort(function (a, b) { return (a.lineup_slot || 99) - (b.lineup_slot || 99) || (a.entry_order || 0) - (b.entry_order || 0); });
      wrap.appendChild(table(
        ["Player", "AB", "R", "H", "HR", "RBI", "BB", "SO"],
        lines.map(function (line) {
          return [
            linkPlayer(code, line.player_id, line.name + (line.is_substitute ? " (sub)" : "")),
            nz(line.ab), nz(line.r), nz(line.h), nz(line.hr), nz(line.rbi), nz(line.bb), nz(line.k)
          ];
        })
      ));
      wrap.appendChild(el("h4", { text: clubName(code) + " pitching" }));
      var arms = game.pitching.filter(function (line) { return line.team === code; })
        .sort(function (a, b) { return a.appearance_order - b.appearance_order; });
      wrap.appendChild(table(
        ["Player", "IP", "H", "R", "ER", "BB", "SO"],
        arms.map(function (line) {
          return [linkPlayer(code, line.player_id, line.name), ipLabel(nz(line.outs)), nz(line.h), nz(line.r), nz(line.er), nz(line.bb), nz(line.k)];
        })
      ));
    });
    return wrap;
  }

  function renderGame(id) {
    markNav("bracket");
    var game = state.games[id];
    clear(view);
    if (!game) {
      view.appendChild(el("p", { text: "That game is not in the archive." }));
      return;
    }
    var page = el("article", { class: "panel" });
    var card = el("div", { class: "scorecard" });
    card.appendChild(el("p", null, el("a", { href: "#/series/" + game.series_id, text: game.series_id })));
    card.appendChild(el("h2", { text: clubName(game.away) + " " + game.score[game.away] + " at " + clubName(game.home) + " " + game.score[game.home] }));
    card.appendChild(el("p", { class: "meta", text: game.id + (game.date ? " · " + game.date : "") + " · " + decisionText(game) }));
    card.appendChild(linescore(game));
    card.appendChild(boxTables(game));
    card.appendChild(el("h4", { text: "Scoring plays" }));
    if (game.scoring_plays && game.scoring_plays.length) {
      var list = el("ol");
      game.scoring_plays.forEach(function (play) { list.appendChild(el("li", { text: play })); });
      card.appendChild(list);
    } else {
      card.appendChild(el("p", { text: "No scoring plays were recorded." }));
    }
    page.appendChild(card);
    var printButton = el("button", { type: "button", class: "copy-button", text: "Print / Save as PDF" });
    printButton.addEventListener("click", function () { window.print(); });
    var tools = el("div", { class: "no-print" });
    tools.appendChild(el("p", { class: "scorecard-actions" },
      printButton,
      el("a", { href: "scorecards/" + game.id + ".pdf", text: "Scorecard PDF" })
    ));
    var chart = wpChart(game);
    if (chart) tools.appendChild(chart);
    tools.appendChild(el("h4", { text: "Recap" }));
    tools.appendChild(el("p", { class: "recap", text: game.game_recap || "No recap was stored." }));
    var turning = narrativeFor(game.id);
    if (turning) tools.appendChild(el("p", { class: "recap", text: turning }));
    if (game.series_recap) tools.appendChild(el("p", { class: "recap", text: game.series_recap }));
    var logHost = el("div");
    tools.appendChild(el("h4", { text: "Manager log" }));
    tools.appendChild(logHost);
    logHost.appendChild(el("p", { class: "muted", text: "Loading the game file…" }));
    var share = el("p", null,
      el("img", { class: "share-card", src: "graphics/games/" + game.id + ".svg", alt: game.id + " final score graphic" })
    );
    tools.appendChild(el("h4", { text: "Share" }));
    tools.appendChild(share);
    tools.appendChild(el("p", null,
      el("a", { href: "graphics/games/" + game.id + ".svg", text: "SVG" }),
      " · ",
      el("a", { href: "graphics/games/" + game.id + ".png", text: "PNG" }),
      " · ",
      el("a", { href: "share/" + game.id + ".html", text: "Share page" }),
      " · ",
      el("a", { href: "box_scores/" + game.id + ".md", text: "Box score markdown" }),
      " · ",
      el("a", { href: "scorecards/" + game.id + ".pdf", text: "Scorecard PDF" })
    ));
    page.appendChild(tools);
    view.appendChild(page);
    var token = ++renderToken;
    var detailUrl = game.detail || ("games/" + game.id + ".json");
    var apply = function (detail) {
      if (token !== renderToken) return;
      clear(logHost);
      var log = detail && detail.manager_log;
      if (!log || !log.length) {
        logHost.appendChild(el("p", { text: "No manager log was recorded for this game." }));
        return;
      }
      var items = el("ol");
      log.forEach(function (entry) {
        items.appendChild(el("li", { text: typeof entry === "string" ? entry : JSON.stringify(entry) }));
      });
      logHost.appendChild(el("details", null, el("summary", { text: log.length + " manager-log lines" }), items));
    };
    if (detailCache[game.id]) {
      apply(detailCache[game.id]);
      return;
    }
    fetch(detailUrl).then(function (response) {
      if (!response.ok) throw new Error(detailUrl);
      return response.json();
    }).then(function (detail) {
      detailCache[game.id] = detail;
      apply(detail);
    }).catch(function () {
      if (token !== renderToken) return;
      clear(logHost);
      logHost.appendChild(el("p", { text: "The game file could not be loaded." }));
    });
  }

  var GROUP_TITLES = { lineup: "Lineup", bench: "Bench", rotation: "Rotation", bullpen: "Bullpen" };

  function cardFor(code, id) {
    return (state.cards && state.cards[code + "|" + id]) || null;
  }

  function rate3(value) {
    if (value == null || isNaN(value)) return "—";
    var text = value.toFixed(3);
    return value < 1 ? text.replace(/^0/, "") : text;
  }

  function bandText(band) {
    return band ? band[0] + "-" + band[1] : "—";
  }

  function spotsText(card) {
    return (card.spots || []).map(function (spot) {
      return (GROUP_TITLES[spot.group] || spot.group) + " " + spot.slot + " · " + spot.pos;
    }).join("; ");
  }

  var PEAK_NOTE = "Counting stats are scaled to a 162-game season. The averages and ERA are that stretch's own, not a tournament stat.";

  function peakYears(row) {
    var years = row && row.window_years;
    if (!years || !years.length) return [];
    return years.slice().sort(function (a, b) { return a - b; });
  }

  function peakLabel(team, years) {
    if (!years || !years.length) return "Peak 162 with " + team;
    var start = years[0];
    var end = years[years.length - 1];
    if (start === end) return "Peak 162 with " + team + " (" + start + ")";
    return "Peak 162 with " + team + " (" + start + "\u2013" + end + ")";
  }

  function peakSections(page, card) {
    if (!card.peak_bat && !card.peak_pit) return;
    var team = (card.peak_bat && card.peak_bat.team_line) || (card.peak_pit && card.peak_pit.team_line) || clubName(card.team);
    var batYears = peakYears(card.peak_bat);
    var pitYears = peakYears(card.peak_pit);
    page.appendChild(el("h3", { text: peakLabel(team, batYears.length ? batYears : pitYears) }));
    page.appendChild(el("p", { class: "note", text: PEAK_NOTE }));
    if (card.peak_bat) {
      var rawBat = card.peak_bat;
      var bat = card.peak_bat_162 || rawBat;
      if (card.peak_pit) page.appendChild(el("h4", { text: "Batting" }));
      var tb = nz(rawBat.H) + nz(rawBat["2B"]) + 2 * nz(rawBat["3B"]) + 3 * nz(rawBat.HR);
      var obpDen = nz(rawBat.AB) + nz(rawBat.BB) + nz(rawBat.HBP) + nz(rawBat.SF);
      page.appendChild(table(
        ["G", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "HBP", "SB", "CS", "AVG", "OBP", "SLG"],
        [[bat.G, bat.PA, bat.AB, bat.R, bat.H, bat["2B"], bat["3B"], bat.HR, bat.RBI, bat.BB, bat.SO, bat.HBP, bat.SB, bat.CS,
          rateLabel(rawBat.H, rawBat.AB), rate3(obpDen ? (nz(rawBat.H) + nz(rawBat.BB) + nz(rawBat.HBP)) / obpDen : null), rate3(rawBat.AB ? tb / rawBat.AB : null)]]));
    }
    if (card.peak_pit) {
      var rawPit = card.peak_pit;
      var pit = card.peak_pit_162 || rawPit;
      var sameYears = batYears.length && pitYears.length && batYears[0] === pitYears[0] && batYears[batYears.length - 1] === pitYears[pitYears.length - 1];
      page.appendChild(el("h4", { text: card.peak_bat && !sameYears ? peakLabel(team, pitYears) : "Pitching" }));
      page.appendChild(table(
        ["W", "L", "G", "GS", "SV", "IP", "H", "R", "ER", "HR", "BB", "SO", "BF", "ERA"],
        [[pit.w, pit.l, pit.g, pit.gs, pit.sv, pit.ip == null ? null : q1(Number(pit.ip)), pit.h, pit.r, pit.er, pit.hr, pit.bb, pit.so, pit.bf,
          eraLabel(nz(rawPit.er), Math.round(Number(rawPit.ip || 0) * 3))]]));
    }
  }

  function factChip(label, value, wide) {
    var text = value == null ? "—" : String(value);
    return el("span", { class: "card-chip" + (wide || text.length > 18 ? " wide" : "") },
      el("span", { class: "card-k", text: label }),
      el("span", { class: "card-v", text: text }));
  }

  function factRow(chips) {
    var kept = chips.filter(Boolean);
    if (!kept.length) return null;
    var row = el("div", { class: "card-facts" });
    kept.forEach(function (chip) { row.appendChild(chip); });
    return row;
  }

  function bandHead(full, short, numeric) {
    return el("th", { class: numeric ? "num" : null, scope: "col" },
      el("span", { class: "wide-label", text: full }),
      el("span", { class: "phone-label", text: short }));
  }

  function cardBandTable(rows) {
    var wrap = el("div", { class: "table-wrap card-band" });
    var t = el("table");
    t.appendChild(el("colgroup", null,
      el("col", { class: "band-result" }),
      el("col", { class: "band-num" }),
      el("col", { class: "band-num" })));
    var head = el("tr");
    head.appendChild(bandHead("Result", "Result", false));
    head.appendChild(bandHead("vs LHP", "vs L", true));
    head.appendChild(bandHead("vs RHP", "vs R", true));
    t.appendChild(el("thead", null, head));
    var body = el("tbody");
    rows.forEach(function (row) {
      var tr = el("tr");
      tr.appendChild(el("td", { text: row[0] }));
      tr.appendChild(el("td", { class: "num", text: row[1] }));
      tr.appendChild(el("td", { class: "num", text: row[2] }));
      body.appendChild(tr);
    });
    t.appendChild(body);
    wrap.appendChild(t);
    return wrap;
  }

  function fieldingLine(positions) {
    var list = el("div", { class: "fielding-line" });
    positions.forEach(function (spot) {
      var row = el("div", { class: "field-row" });
      row.appendChild(el("span", { class: "field-pos", text: spot.pos || "" }));
      if (spot.range != null && spot.range !== "") row.appendChild(factChip("Range", spot.range));
      if (spot.e != null && spot.e !== "") row.appendChild(factChip("E", spot.e));
      if (spot.arm != null && spot.arm !== "") row.appendChild(factChip("Arm", spot.arm));
      list.appendChild(row);
    });
    return list;
  }

  function diceGrid(table) {
    var grid = el("div", { class: "dice-grid" });
    ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"].forEach(function (total) {
      var text = table[total] || "—";
      grid.appendChild(el("div", { class: "dice-cell" + (text.length > 12 ? " wide" : "") },
        el("span", { class: "card-k", text: total }),
        el("span", { class: "card-v", text: text })));
    });
    return grid;
  }

  function cardSections(page, card) {
    if (!card.card_bat && !card.card_pit) return;
    var block = el("section", { class: "payoff-card" });
    block.appendChild(el("h3", { text: "Payoff Pitch card" }));
    if (card.card_bat) {
      var bat = card.card_bat;
      block.appendChild(el("h4", { text: "Hitter card" }));
      var bits = [];
      if (bat.bats) bits.push(factChip("Bats", bat.bats));
      if (bat.throws) bits.push(factChip("Throws", bat.throws));
      if (bat.run != null) bits.push(factChip("Run", bat.run));
      if (bat.steal) bits.push(factChip("Steal", bat.steal.rating + (bat.steal.jump != null ? ", jump " + bat.steal.jump : "")));
      if (bat.sac_bunt) bits.push(factChip("Sac bunt", bat.sac_bunt));
      if (bat.dp != null) bits.push(factChip("DP", bat.dp));
      if (bat.fielding) bits.push(factChip("Fielding", bat.fielding));
      if (bat.arm) bits.push(factChip("Arm", bat.arm));
      var facts = factRow(bits);
      if (facts) block.appendChild(facts);
      if (bat.positions && bat.positions.length) block.appendChild(fieldingLine(bat.positions));
      ["WHEELHOUSE", "PATIENT", "TOUGH", "IN-PLAY"].forEach(function (name) {
        var section = bat.sections && bat.sections[name];
        if (!section) return;
        block.appendChild(el("p", { class: "meta", text: name + " (percentile bands)" }));
        var rows = ["HR", "3B", "2B", "1B", "BB", "HBP", "SO"].filter(function (result) {
          return (section.vsLHP && section.vsLHP[result]) || (section.vsRHP && section.vsRHP[result]);
        }).map(function (result) {
          return [result, bandText(section.vsLHP && section.vsLHP[result]), bandText(section.vsRHP && section.vsRHP[result])];
        });
        if (rows.length) block.appendChild(cardBandTable(rows));
      });
      if (bat.out_table && bat.out_table.length) {
        block.appendChild(el("p", { class: "note", text: "Out table: " + bat.out_table.map(function (row) {
          return row.range[0] + "-" + row.range[1] + " " + row.result;
        }).join(" · ") }));
      }
      if (bat.qa_status) block.appendChild(el("p", { class: "note", text: "Card QA: " + bat.qa_status + "." }));
    }
    if (card.card_pit) {
      var pit = card.card_pit;
      block.appendChild(el("h4", { text: "Pitcher card (v2)" }));
      var pbits = [];
      if (pit.throws) pbits.push(factChip("Throws", pit.throws));
      if (pit.card_type) pbits.push(factChip("Type", pit.card_type));
      if (pit.so_modifier) pbits.push(factChip("SO modifier", pit.so_modifier));
      if (pit.special && pit.special.length) pbits.push(factChip("Special", pit.special.join(", "), true));
      if (pit.stamina) {
        if (pit.stamina.start != null) pbits.push(factChip("Start", pit.stamina.start));
        if (pit.stamina.relief) pbits.push(factChip("Relief", pit.stamina.relief));
      }
      if (pit.addendum) {
        [["wp", "WP"], ["dp", "DP"], ["hold", "Hold"], ["pickoff", "Pickoff"], ["inj", "Inj"]].forEach(function (pair) {
          var value = pit.addendum[pair[0]];
          if (value != null && value !== "") pbits.push(factChip(pair[1], value));
        });
      }
      var pfacts = factRow(pbits);
      if (pfacts) block.appendChild(pfacts);
      if (pit.table_2d6) {
        block.appendChild(el("p", { class: "meta", text: "2d6 section" }));
        block.appendChild(diceGrid(pit.table_2d6));
      }
      if (pit.qa_status) block.appendChild(el("p", { class: "note", text: "Card QA: " + pit.qa_status + "." }));
    }
    page.appendChild(block);
  }

  function isNameStart(token) {
    if (/^[A-Z](?:\.[A-Z]\.?)+$/.test(token)) return true;
    if (/^(DJ|AJ|JJ)$/.test(token)) return true;
    if (token.indexOf("/") !== -1 || /\d/.test(token)) return false;
    return /[a-zà-ÿ]/.test(token);
  }

  function isYearToken(token) {
    return /^\(?\d+\)?$/.test(token) || /^\d{4}(?:-\d{2,4})?,?$/.test(token);
  }

  function isPosToken(token) {
    return /^(?:C|1B|2B|3B|SS|LF|CF|RF|DH|OF|IF|SP|RP|P|UT|INF|CI|MI|PH)(?:\/(?:C|1B|2B|3B|SS|LF|CF|RF|DH|OF|IF|SP|RP|P|UT|INF|CI|MI|PH|Bat|Power|Utility|PR|DEF))*$/i.test(token);
  }

  function splitRosterLine(line) {
    var tokens = String(line || "").trim().split(/\s+/).filter(Boolean);
    var i = 0;
    while (i < tokens.length && !isNameStart(tokens[i])) i += 1;
    if (!tokens.length || i === 0 || i >= tokens.length) return { slot: "", name: tokens.join(" "), pos: "", meta: "" };
    var rest = tokens.slice(i);
    var meta = [];
    function peelYears() {
      while (rest.length > 1 && (isYearToken(rest[rest.length - 1]) || /^[LRS]$/.test(rest[rest.length - 1]))) {
        meta.unshift(rest.pop());
      }
    }
    peelYears();
    var pos = "";
    var tail = rest[rest.length - 1];
    if (rest.length > 2 && /^(Utility|Power|Bat)$/i.test(tail) && isPosToken(rest[rest.length - 2])) {
      var word = rest.pop();
      pos = rest.pop() + " " + word;
      peelYears();
    } else if (rest.length > 1 && isPosToken(tail)) {
      pos = rest.pop();
      peelYears();
    }
    return { slot: tokens.slice(0, i).join(" "), name: rest.join(" "), pos: pos, meta: meta.join(" ") };
  }

  function rosterTable(rows) {
    var showSlot = rows.some(function (row) { return row.slot; });
    var showPos = rows.some(function (row) { return row.pos; });
    var longest = 0;
    rows.forEach(function (row) { longest = Math.max(longest, String(row.slot || "").length); });
    var slotSize = longest <= 2 ? " slot-num" : longest <= 4 ? " slot-mid" : " slot-wide";
    var wrap = el("div", { class: "table-wrap roster-fit" });
    var t = el("table", { class: "roster-table" + (showSlot ? " has-slot" + slotSize : " no-slot") + (showPos ? " has-pos" : " no-pos") });
    if (showSlot || showPos) {
      var head = el("tr");
      if (showSlot) head.appendChild(el("th", { text: "Slot" }));
      head.appendChild(el("th", { text: "Player" }));
      if (showPos) head.appendChild(el("th", { text: "Pos" }));
      t.appendChild(el("thead", null, head));
    }
    var body = el("tbody");
    rows.forEach(function (row) {
      var tr = el("tr");
      if (showSlot) tr.appendChild(el("td", { class: "roster-slot", text: row.slot || "" }));
      var who = el("td", { class: "roster-who" });
      if (row.name && row.name.nodeType) who.appendChild(row.name);
      else who.appendChild(el("span", { class: "roster-player", text: row.name || "" }));
      if (row.meta) who.appendChild(el("span", { class: "roster-meta", text: row.meta }));
      if (row.peak) who.appendChild(el("span", { class: "roster-peak muted", text: row.peak }));
      tr.appendChild(who);
      if (showPos) tr.appendChild(el("td", { class: "roster-pos", text: row.pos || "" }));
      body.appendChild(tr);
    });
    t.appendChild(body);
    wrap.appendChild(t);
    return wrap;
  }

  function rosterSection(page, code, collapsed) {
    var roster = state.rosters && state.rosters[code];
    if (!roster) return;
    var body = el("div");
    body.appendChild(el("p", { class: "note", text: "The converted set, in set order. Open a player for his card and his tournament line." }));
    ["lineup", "bench", "rotation", "bullpen"].forEach(function (group) {
      var rows = roster.players.filter(function (spot) { return spot.group === group; })
        .sort(function (a, b) { return a.slot - b.slot; });
      if (!rows.length) return;
      body.appendChild(el("h4", { text: GROUP_TITLES[group] }));
      body.appendChild(rosterTable(rows.map(function (spot) {
        return { slot: String(spot.slot), name: linkPlayer(code, spot.id, spot.name), pos: spot.pos };
      })));
    });
    if (collapsed) {
      var details = el("details", { class: "card-set" });
      details.appendChild(el("summary", { text: "Payoff Pitch cards" }));
      details.appendChild(body);
      page.appendChild(details);
      return;
    }
    page.appendChild(el("h3", { text: "Payoff Pitch cards" }));
    page.appendChild(body);
  }

  function renderRosters() {
    if (!state.cardsLoaded) {
      loadOnDemand("cards", renderRosters);
      return;
    }
    markNav("rosters");
    clear(view);
    var page = el("section");
    page.appendChild(el("h2", { text: "Rosters and player cards" }));
    page.appendChild(el("p", { class: "note", text: "Converted Payoff Pitch cards exist for 11 clubs (ARI, BOS, CHC, COL, DET, MON, PHA, SF, STL, TB, WSH). Every club's roster is on its team page." }));
    var clubs = Object.keys(state.rosters || {}).map(function (code) { return state.rosters[code]; })
      .sort(function (a, b) { return a.seed - b.seed; });
    if (!clubs.length) page.appendChild(el("p", { text: "No converted sets are on file yet." }));
    clubs.forEach(function (roster) {
      var ids = {};
      var withLines = 0;
      Object.keys(state.cards || {}).forEach(function (key) {
        var card = state.cards[key];
        if (card.team !== roster.code) return;
        ids[card.id] = true;
        if (card.tournament) withLines += 1;
      });
      var team = state.byCode[roster.code];
      var panel = el("section", { class: "panel" });
      panel.appendChild(el("h3", null, linkTeam(roster.code, roster.name)));
      panel.appendChild(el("p", { class: "meta", text:
        "Seed " + roster.seed +
        (team ? " · series " + team.series_wins + "-" + team.series_losses + " · games " + team.game_wins + "-" + team.game_losses : "") +
        " · " + Object.keys(ids).length + " players · " + withLines + " with tournament lines" +
        (roster.played ? "" : " · no tournament games yet") }));
      page.appendChild(panel);
    });
    view.appendChild(page);
  }

  function renderTeam(code) {
    if (state.announced && state.announced[code] && !state.peakLoaded) {
      loadOnDemand("peak", function () { renderTeam(code); });
      return;
    }
    markNav("standings");
    var team = state.byCode[code];
    clear(view);
    if (!team) {
      view.appendChild(el("p", { text: "That club is not in the field." }));
      return;
    }
    var diff = runDiff()[code];
    var page = el("article", { class: "panel" });
    var hero = el("div", { class: "team-hero" });
    hero.appendChild(logo(team, team.name + " mark"));
    hero.appendChild(el("div", null,
      el("h2", { text: "#" + team.seed + " " + team.name }),
      el("p", { class: "meta", text: team.code + " · " + (team.bracket || "winners") + " bracket · series " + team.series_wins + "-" + team.series_losses + " · games " + team.game_wins + "-" + team.game_losses })
    ));
    page.appendChild(hero);
    page.appendChild(el("p", { class: "muted", text: markNote(team.code) }));
    page.appendChild(el("p", { text: "Run differential " + (diff.rs - diff.ra) + " (" + diff.rs + " scored, " + diff.ra + " allowed)." }));
    if (team.game_wins + team.game_losses > 0) {
      var split = teamSplits()[code] || { home: [0, 0], away: [0, 0], extra: [0, 0], one: [0, 0] };
      page.appendChild(el("p", { text: "Home " + recordPair(split.home) + ", away " + recordPair(split.away) + ", extra innings " + recordPair(split.extra) + ", one-run " + recordPair(split.one) + "." }));
    }
    page.appendChild(el("h3", { text: "Results" }));
    var any = false;
    state.data.series.forEach(function (series) {
      if (series.team_a !== code && series.team_b !== code) return;
      if (!(series.games || []).length && series.status === "awaiting-feeders") return;
      any = true;
      var block = el("div");
      block.appendChild(el("p", null, el("a", { href: "#/series/" + series.id, text: series.id }), " ", STATUS[series.status] || series.status));
      (series.games || []).forEach(function (gameId) {
        var game = state.games[gameId];
        if (!game) return;
        var opp = game.home === code ? game.away : game.home;
        var mark = game.winner === code ? "W" : "L";
        block.appendChild(el("p", null, linkGame(game.id, game.id), " " + mark + " " + game.score[code] + "-" + game.score[opp] + " vs " + clubName(opp)));
      });
      page.appendChild(block);
    });
    if (!any) page.appendChild(el("p", { text: "No series played yet." }));
    var batRows = [];
    var pitRows = [];
    Object.keys(state.players).forEach(function (key) {
      var player = state.players[key];
      if (player.team !== code) return;
      if (paOf(player.bat) > 0) {
        batRows.push([
          linkPlayer(code, player.id, player.name),
          paOf(player.bat), player.bat.ab, player.bat.h, player.bat.hr, player.bat.rbi,
          rateLabel(player.bat.h, player.bat.ab)
        ]);
      }
      if (player.pit.outs + player.pit.w + player.pit.sv > 0) {
        pitRows.push([
          linkPlayer(code, player.id, player.name),
          ipLabel(player.pit.outs), player.pit.w, player.pit.l, player.pit.sv, player.pit.k,
          eraLabel(player.pit.er, player.pit.outs)
        ]);
      }
    });
    var announced = state.announced && state.announced[code];
    if (announced) page.appendChild(announcedRoster(announced, code));
    rosterSection(page, code, !!announced);
    if (batRows.length || pitRows.length) page.appendChild(el("h3", { text: "Roster stats" }));
    else if (!announced && !(state.rosters && state.rosters[code])) {
      page.appendChild(el("h3", { text: "Roster" }));
      page.appendChild(el("p", { text: "Roster not announced yet." }));
    }
    if (batRows.length) {
      page.appendChild(el("h4", { text: "Batting" }));
      page.appendChild(table(["Player", "PA", "AB", "H", "HR", "RBI", "AVG"], batRows));
    }
    if (pitRows.length) {
      page.appendChild(el("h4", { text: "Pitching" }));
      page.appendChild(table(["Player", "IP", "W", "L", "SV", "K", "ERA"], pitRows));
    }
    view.appendChild(page);
  }

  function peakLine(code, line) {
    var book = state.peak && state.peak.clubs && state.peak.clubs[code];
    var row = book && book[line];
    if (!row || row.status !== "ok" || !row.text) return "Peak stats unavailable";
    return row.text;
  }

  function rosterGroup(code, title, lines) {
    var block = el("div");
    block.appendChild(el("h4", { text: title }));
    block.appendChild(rosterTable((lines || []).map(function (line) {
      var parts = splitRosterLine(line);
      return { slot: parts.slot, name: parts.name, pos: parts.pos, meta: parts.meta, peak: peakLine(code, line) };
    })));
    return block;
  }

  function announcedRoster(roster, code) {
    var headers = roster.headers || {};
    var block = el("div", { class: "roster" });
    block.appendChild(el("h3", { text: "Roster" }));
    block.appendChild(el("p", { class: "note", text: "Official roster from the tournament owner. " + PEAK_NOTE }));
    block.appendChild(el("p", { text: "Manager: " + roster.manager }));
    block.appendChild(rosterGroup(code, headers.lineup || "Lineup", roster.lineup));
    block.appendChild(rosterGroup(code, headers.bench || "Bench", roster.bench));
    block.appendChild(rosterGroup(code, headers.rotation || "Rotation", roster.rotation));
    block.appendChild(rosterGroup(code, headers.bullpen || "Bullpen", roster.bullpen));
    if ((roster.honorable_mentions || []).length) {
      var title = "Honorable mentions";
      if (roster.honorable_note) title += " (" + roster.honorable_note + ")";
      var honors = rosterGroup(code, title, roster.honorable_mentions);
      var head = honors.querySelector("h4");
      honors.insertBefore(el("p", { class: "note", text: "These names are not on the active roster." }), head.nextSibling);
      block.appendChild(honors);
    }
    if (roster.what_if) {
      block.appendChild(rosterGroup(code, roster.what_if_label || "What if", [roster.what_if]));
    }
    return block;
  }

  function renderPlayer(code, id) {
    if (!state.cardsLoaded) {
      loadOnDemand("cards", function () { renderPlayer(code, id); });
      return;
    }
    markNav("standings");
    var player = state.players[code + "|" + id];
    var card = cardFor(code, id);
    clear(view);
    if (!player && card) {
      var onlyPage = el("article", { class: "panel" });
      var onlyTeam = state.byCode[code];
      var onlyHero = el("div", { class: "player-hero" });
      if (onlyTeam) onlyHero.appendChild(logo(onlyTeam));
      onlyHero.appendChild(el("div", null,
        el("h2", { text: card.name }),
        el("p", { class: "meta" }, linkTeam(code), " · " + id)
      ));
      onlyPage.appendChild(onlyHero);
      if (spotsText(card)) onlyPage.appendChild(el("p", { class: "meta", text: spotsText(card) }));
      onlyPage.appendChild(el("h3", { text: "Tournament" }));
      var roster = state.rosters && state.rosters[code];
      onlyPage.appendChild(el("p", { text: roster && !roster.played
        ? clubName(code) + " has not played a tournament game yet. The peak line and the card are below."
        : "No appearances in the tournament yet. The peak line and the card are below." }));
      peakSections(onlyPage, card);
      cardSections(onlyPage, card);
      view.appendChild(onlyPage);
      return;
    }
    if (!player) {
      view.appendChild(el("p", { text: "That player has no line in the archive." }));
      return;
    }
    var page = el("article", { class: "panel" });
    var team = state.byCode[code];
    var hero = el("div", { class: "player-hero" });
    if (team) hero.appendChild(logo(team));
    hero.appendChild(el("div", null,
      el("h2", { text: player.name }),
      el("p", { class: "meta" }, linkTeam(code), " · " + player.id)
    ));
    page.appendChild(hero);
    var bio = state.bios && state.bios[code + "|" + id];
    if (bio && bio.bio) {
      page.appendChild(el("h3", { text: "Bio" }));
      page.appendChild(el("p", { text: bio.bio }));
      if (bio.career) page.appendChild(el("p", { class: "muted", text: bio.career }));
    }
    if (card) {
      peakSections(page, card);
      cardSections(page, card);
    }
    if (paOf(player.bat) > 0) {
      page.appendChild(el("h3", { text: "Tournament batting" }));
      var batGames = {};
      player.log.forEach(function (item) { if (item.side === "bat") batGames[item.game] = true; });
      var obpDen = player.bat.ab + player.bat.bb + player.bat.hbp + player.bat.sf;
      page.appendChild(table(
        ["G", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "SB", "AVG", "OBP", "SLG"],
        [[
          Object.keys(batGames).length,
          player.bat.ab, player.bat.r, player.bat.h, player.bat.doubles, player.bat.triples,
          player.bat.hr, player.bat.rbi, player.bat.bb, player.bat.k, player.bat.sb,
          rateLabel(player.bat.h, player.bat.ab),
          rate3(obpDen ? (player.bat.h + player.bat.bb + player.bat.hbp) / obpDen : null),
          rate3(player.bat.ab ? totalBases(player.bat) / player.bat.ab : null)
        ]]
      ));
      var streak = hitStreak(player);
      page.appendChild(el("p", { text: "Hit streak " + streak.currentHit + " (longest " + streak.longestHit + "). Cold streak " + streak.currentCold + " (longest " + streak.longestCold + ")." }));
    }
    if (player.pit.outs + player.pit.w + player.pit.l + player.pit.sv > 0) {
      page.appendChild(el("h3", { text: "Tournament pitching" }));
      var pitGames = {};
      player.log.forEach(function (item) { if (item.side === "pit") pitGames[item.game] = true; });
      page.appendChild(table(
        ["G", "GS", "W", "L", "SV", "IP", "H", "R", "ER", "BB", "SO", "HR", "ERA"],
        [[Object.keys(pitGames).length, player.pit.gs, player.pit.w, player.pit.l, player.pit.sv, ipLabel(player.pit.outs), player.pit.h, player.pit.r, player.pit.er, player.pit.bb, player.pit.k, player.pit.hr, eraLabel(player.pit.er, player.pit.outs)]]
      ));
      var last = null;
      workloadRows().forEach(function (item) {
        if (item.line.team === code && item.line.player_id === id) last = item;
      });
      if (last) {
        page.appendChild(el("p", { text: "Last outing " + last.game.id + ": " + ipLabel(nz(last.line.outs)) + " IP, " + (last.line.bf == null ? "batters faced not stored" : last.line.bf + " BF") + ", pitches " + last.pitches + ". Rest before that outing: " + last.rest + ". Fatigue: " + last.fatigue + "." }));
      }
    }
    page.appendChild(el("h3", { text: "Grades" }));
    if (!player.grades.length) {
      page.appendChild(el("p", { text: "No letter grade is stored for this player. Payoff Pitch games keep final_grades empty." }));
    } else {
      page.appendChild(table(
        ["Game", "Grade"],
        player.grades.map(function (item) { return [linkGame(item.game), item.grade]; })
      ));
    }
    page.appendChild(el("h3", { text: "Game log" }));
    page.appendChild(table(
      ["Game", "Role", "Line"],
      player.log.map(function (item) {
        var summary = item.side === "bat"
          ? nz(item.line.ab) + " AB, " + nz(item.line.h) + " H, " + nz(item.line.hr) + " HR, " + nz(item.line.rbi) + " RBI"
          : ipLabel(nz(item.line.outs)) + " IP, " + nz(item.line.er) + " ER, " + nz(item.line.k) + " K";
        return [linkGame(item.game), item.side === "bat" ? "Batting" : "Pitching", summary];
      })
    ));
    view.appendChild(page);
  }

  function awardTable(title, note, rows, cells) {
    return el("section", null,
      el("h3", { text: title }),
      el("p", { class: "note", text: note }),
      table(["Player", "Team", "Pts"].concat(cells.headers), rows.slice(0, 15).map(function (row) {
        return [linkPlayer(row.player.team, row.player.id, row.player.name), clubName(row.player.team), q1(row.points)].concat(cells.values(row));
      }))
    );
  }

  function renderAwards() {
    markNav("awards");
    var board = awards();
    var page = el("article");
    page.appendChild(el("h2", { text: "Awards race" }));
    page.appendChild(el("p", { class: "note", text: "Display points from MODELS.md. Not an official vote." }));
    page.appendChild(awardTable(
      "Most valuable player",
      "Total bases + R + RBI + SB + 0.5×BB + 0.5×HBP − CS.",
      board.mvp,
      { headers: ["HR", "RBI"], values: function (row) { return [row.player.bat.hr, row.player.bat.rbi]; } }
    ));
    page.appendChild(awardTable(
      "Cy Young",
      "Pitchers with at least one start. IP + 0.4×K + 5×W − 1.5×ER − 0.3×BB.",
      board.cy,
      { headers: ["IP", "W", "K"], values: function (row) { return [ipLabel(row.player.pit.outs), row.player.pit.w, row.player.pit.k]; } }
    ));
    page.appendChild(awardTable(
      "Reliever",
      "Pitchers with zero starts. 5×SV + 2×IP + 0.4×K − 1.5×ER.",
      board.rel,
      { headers: ["SV", "IP", "K"], values: function (row) { return [row.player.pit.sv, ipLabel(row.player.pit.outs), row.player.pit.k]; } }
    ));
    clear(view);
    view.appendChild(page);
  }

  function renderRecords() {
    markNav("records");
    var found = milestones();
    var page = el("article", { class: "stack" });
    page.appendChild(el("h2", { text: "Records and milestones" }));
    page.appendChild(el("p", { class: "note", text: "Bars from MODELS.md, counted only from the box scores." }));
    page.appendChild(el("h3", { text: "No-hitters" }));
    if (!found.nohitters.length) page.appendChild(el("p", { text: "None on record." }));
    found.nohitters.forEach(function (item) {
      page.appendChild(el("p", null,
        linkPlayer(item.line.team, item.line.player_id, item.line.name),
        " ",
        linkGame(item.game.id),
        " " + ipLabel(item.line.outs) + " IP, 0 H, " + nz(item.line.k) + " K"
      ));
    });
    page.appendChild(el("h3", { text: "Ten or more strikeouts" }));
    found.highK.forEach(function (item) {
      page.appendChild(el("p", null,
        linkPlayer(item.line.team, item.line.player_id, item.line.name),
        " " + nz(item.line.k) + " K in ",
        linkGame(item.game.id)
      ));
    });
    page.appendChild(el("h3", { text: "Games with 10 or more runs" }));
    found.big.forEach(function (item) {
      page.appendChild(el("p", null, linkTeam(item.code), " scored " + item.game.score[item.code] + " in ", linkGame(item.game.id)));
    });
    clear(view);
    view.appendChild(page);
  }

  function renderStandings() {
    markNav("standings");
    var diff = runDiff();
    var rows = state.data.teams.slice().sort(function (a, b) { return a.seed - b.seed; }).map(function (team) {
      var line = diff[team.code];
      var rd = line.rs - line.ra;
      return [
        String(team.seed),
        linkTeam(team.code, team.name),
        team.bracket || "",
        team.series_wins + "-" + team.series_losses,
        team.game_wins + "-" + team.game_losses,
        String(rd)
      ];
    });
    clear(view);
    view.appendChild(el("section", null,
      el("h2", { text: "Standings" }),
      el("p", { class: "note", text: "Run differential is runs scored minus runs allowed. Series losses, not this table, decide the bracket." }),
      table(["Seed", "Team", "Bracket", "Series", "Games", "Diff"], rows)
    ));
  }

  function renderSearch(query) {
    var needle = (query || "").trim().toLowerCase();
    if (needle && !state.cardsLoaded) {
      loadOnDemand("cards", function () { renderSearch(query); });
      return;
    }
    markNav("standings");
    clear(view);
    var page = el("section");
    page.appendChild(el("h2", { text: "Player search" }));
    if (!needle) {
      page.appendChild(el("p", { text: "Type a name in the search box." }));
      view.appendChild(page);
      return;
    }
    var hits = Object.keys(state.players).map(function (key) { return state.players[key]; }).filter(function (player) {
      return player.name.toLowerCase().indexOf(needle) !== -1 || player.team.toLowerCase().indexOf(needle) !== -1 || player.id.toLowerCase().indexOf(needle) !== -1;
    });
    Object.keys(state.cards || {}).forEach(function (key) {
      if (state.players[key]) return;
      var card = state.cards[key];
      if (card.name.toLowerCase().indexOf(needle) !== -1 || card.team.toLowerCase().indexOf(needle) !== -1 || card.id.toLowerCase().indexOf(needle) !== -1) {
        hits.push({ name: card.name, team: card.team, id: card.id });
      }
    });
    hits.sort(function (a, b) { return a.name.localeCompare(b.name) || a.team.localeCompare(b.team); });
    if (!hits.length) page.appendChild(el("p", { text: "No matching player line." }));
    hits.forEach(function (player) {
      page.appendChild(el("p", null, linkPlayer(player.team, player.id, player.name), " · ", linkTeam(player.team)));
    });
    view.appendChild(page);
  }

  function markNote(code) {
    var colors = teamColors(code);
    if (colors && colors.mark === "monogram") {
      return "Monogram in team colors. " + (colors.color_source || "") + " Swap the file in data/teams.json.";
    }
    if (colors) return "Logo file (" + colors.mark + "). Swap the file in data/teams.json.";
    return "Swap the file in data/teams.json.";
  }

  function titleStrip() {
    if (!state.odds || !state.odds.title) return null;
    var rows = Object.keys(state.odds.title).map(function (code) {
      return { code: code, p: Number(state.odds.title[code]) };
    }).filter(function (row) { return row.p > 0; }).sort(function (a, b) {
      return b.p - a.p || a.code.localeCompare(b.code);
    });
    if (!rows.length) return null;
    var line = el("p");
    rows.forEach(function (row, index) {
      if (index) line.appendChild(document.createTextNode(" · "));
      line.appendChild(linkTeam(row.code));
      line.appendChild(document.createTextNode(" " + percent(row.p) + "%"));
    });
    return el("section", { class: "title-odds" },
      el("h2", { text: "Title odds" }),
      el("p", { class: "note", text: "Monte Carlo, 4,000 draws, from each club's index. Clubs at 0.0% won none of those draws. The model is in MODELS.md and does not change a result." }),
      line
    );
  }

  function renderBanner() {
    clear(banner);
    if (!state.data) {
      banner.hidden = true;
      return;
    }
    var found = milestones();
    if (!found.nohitters.length) {
      banner.hidden = true;
      return;
    }
    banner.hidden = false;
    var item = found.nohitters[0];
    banner.appendChild(document.createTextNode(item.line.name + " no-hitter · "));
    banner.appendChild(linkGame(item.game.id, item.game.id));
    if (found.nohitters.length > 1) {
      banner.appendChild(document.createTextNode(" · " + found.nohitters.length + " on the book"));
    }
  }

  function renderPreviews() {
    markNav("previews");
    var page = el("article", { class: "stack" });
    page.appendChild(el("h2", { text: "Matchup previews" }));
    page.appendChild(el("p", { class: "note", text: "Starters are taken from a series carry file when one is stored. Key players are taken from box scores already played. Nothing here is a proposed roster." }));
    var shown = 0;
    state.data.series.forEach(function (series) {
      if (!series.team_a || !series.team_b) return;
      if (series.status !== "in-progress" && series.status !== "scheduled") return;
      shown += 1;
      page.appendChild(previewCard(series));
    });
    if (!shown) page.appendChild(el("p", { text: "No series is scheduled or in progress." }));
    clear(view);
    view.appendChild(page);
  }

  function previewCard(series) {
    var card = el("section", { class: "panel preview-card" });
    card.appendChild(el("h3", { text: series.label || series.id }));
    card.appendChild(el("p", { class: "meta", text: series.id + " · " + (STATUS[series.status] || series.status) }));
    card.appendChild(el("p", null, linkTeam(series.team_a), " vs ", linkTeam(series.team_b)));
    card.appendChild(oddsBar(series));
    var number = (series.games || []).length + 1;
    var home = (series.home_by_game || {})[String(number)];
    if (home && series.status === "in-progress") {
      var away = home === series.team_a ? series.team_b : series.team_a;
      var starters = (series.carry && series.carry.rotation_next_start) || {};
      var awayStarter = starters[away] || "not named in the carry file";
      var homeStarter = starters[home] || "not named in the carry file";
      card.appendChild(el("p", { text: "Game " + number + " at " + clubName(home) + ": " + awayStarter + " (" + away + ") at " + homeStarter + " (" + home + ")." }));
      if (series.carry && series.carry.rotation_note) {
        card.appendChild(el("p", { class: "muted", text: series.carry.rotation_note }));
      }
    } else if (series.status === "scheduled") {
      var firstHome = (series.home_by_game || {})["1"];
      card.appendChild(el("p", { text: firstHome ? "Game 1 is at " + clubName(firstHome) + ". No probable starter is stored." : "No probable starter is stored." }));
    }
    card.appendChild(el("h4", { text: "Strength" }));
    [series.team_a, series.team_b].forEach(function (code) {
      var team = state.byCode[code];
      var title = state.odds && state.odds.title ? state.odds.title[code] : null;
      var text = clubName(code) + " index " + (team ? team.index : "—");
      if (title != null) text += ", title " + percent(title) + "%";
      card.appendChild(el("p", { text: text }));
    });
    var played = (series.games || []).map(function (id) { return state.games[id]; }).filter(Boolean);
    card.appendChild(el("h4", { text: "Head to head" }));
    if (!played.length) {
      card.appendChild(el("p", { text: "These clubs have not played in this tournament." }));
    } else {
      played.forEach(function (game) {
        card.appendChild(el("p", null,
          linkGame(game.id, "Game " + game.game_in_series),
          " ",
          clubName(game.away) + " " + game.score[game.away] + ", " + clubName(game.home) + " " + game.score[game.home]
        ));
      });
    }
    card.appendChild(el("h4", { text: "Key players" }));
    var keys = [];
    played.forEach(function (game) {
      game.pitching.forEach(function (line) {
        if (line.appearance_order === 1 || nz(line.k) >= 10 || (line.appearance_order === 1 && nz(line.h) === 0 && nz(line.outs) >= 27)) {
          keys.push(linkPlayer(line.team, line.player_id, line.name) );
          keys.push(document.createTextNode(" " + ipLabel(nz(line.outs)) + " IP, " + nz(line.h) + " H, " + nz(line.k) + " K in " + game.id));
          keys.push(el("br"));
        }
      });
      game.batting.forEach(function (line) {
        if (nz(line.hr) > 0 || nz(line.h) >= 3) {
          keys.push(linkPlayer(line.team, line.player_id, line.name));
          keys.push(document.createTextNode(" " + nz(line.h) + " H, " + nz(line.hr) + " HR in " + game.id));
          keys.push(el("br"));
        }
      });
    });
    if (!keys.length) card.appendChild(el("p", { text: "No box score yet, so no key players are listed." }));
    else {
      var block = el("p");
      keys.forEach(function (node) { block.appendChild(node); });
      card.appendChild(block);
    }
    card.appendChild(el("p", null, el("a", { href: "#/series/" + series.id, text: "Open " + series.id })));
    return card;
  }

  function hitStreak(player) {
    var games = player.log.filter(function (item) { return item.side === "bat"; });
    var run = 0;
    var cold = 0;
    var longestHit = 0;
    var longestCold = 0;
    games.forEach(function (item, index) {
      if (nz(item.line.h) > 0) {
        run += 1;
        cold = 0;
        if (run > longestHit) longestHit = run;
      } else {
        run = 0;
        cold += 1;
        if (cold > longestCold) longestCold = cold;
      }
      if (index === games.length - 1) {
        player._hit = run;
        player._cold = cold;
      }
    });
    if (!games.length) {
      player._hit = 0;
      player._cold = 0;
    }
    return { games: games.length, currentHit: player._hit || 0, longestHit: longestHit, currentCold: player._cold || 0, longestCold: longestCold };
  }

  function ownedInnings(arms) {
    var total = arms.reduce(function (sum, arm) { return sum + nz(arm.outs); }, 0);
    if (!total) return {};
    var last = total % 3 === 0 ? 3 : total % 3;
    var count = Math.floor(total / 3) + (total % 3 ? 1 : 0);
    function lengthOf(inning) { return inning === count ? last : 3; }
    var buckets = {};
    var inning = 1;
    var used = 0;
    arms.forEach(function (arm) {
      var left = nz(arm.outs);
      while (left > 0) {
        var take = Math.min(left, lengthOf(inning) - used);
        if (!buckets[inning]) buckets[inning] = [];
        buckets[inning].push(arm);
        used += take;
        left -= take;
        if (used >= lengthOf(inning)) {
          inning += 1;
          used = 0;
        }
      }
    });
    var owned = {};
    Object.keys(buckets).forEach(function (key) {
      var ids = {};
      buckets[key].forEach(function (arm) { ids[arm.player_id] = arm; });
      var names = Object.keys(ids);
      owned[key] = names.length === 1 ? ids[names[0]] : null;
    });
    return owned;
  }

  var PLATE = { K: 1, OUT: 1, HIT: 1, BB: 1, HBP: 1, ERR: 1, DP: 1, FC: 1 };

  function matchupRows() {
    var rows = {};
    var skipped = 0;
    var named = 0;
    state.data.games.forEach(function (game) {
      var detail = detailCache[game.id];
      var rolls = detail && detail.rolls;
      if (!rolls || !rolls.length || !rolls[0] || !rolls[0].player_id) return;
      named += 1;
      var byTeam = {};
      [game.home, game.away].forEach(function (code) {
        var arms = game.pitching.filter(function (line) { return line.team === code; })
          .sort(function (a, b) { return a.appearance_order - b.appearance_order; });
        byTeam[code] = ownedInnings(arms);
      });
      rolls.forEach(function (roll) {
        if (!PLATE[roll.kind]) return;
        var defense = roll.half === "top" ? game.home : game.away;
        var arm = byTeam[defense][String(roll.inning)];
        if (!arm) {
          skipped += 1;
          return;
        }
        var key = roll.team + "|" + roll.player_id + "|" + arm.team + "|" + arm.player_id;
        if (!rows[key]) {
          rows[key] = {
            batterTeam: roll.team, batterId: roll.player_id, batter: roll.batter,
            pitcherTeam: arm.team, pitcherId: arm.player_id, pitcher: arm.name,
            pa: 0, ab: 0, h: 0, hr: 0, bb: 0, k: 0
          };
        }
        var row = rows[key];
        row.pa += 1;
        if (roll.kind === "HIT") {
          row.h += 1;
          row.ab += 1;
          if (/HOME RUN/i.test(roll.result_text || "")) row.hr += 1;
        } else if (roll.kind === "K") {
          row.k += 1;
          row.ab += 1;
        } else if (roll.kind === "BB") {
          row.bb += 1;
        } else if (roll.kind === "HBP") {
          /* plate appearance, not an at-bat */
        } else if (roll.kind === "ERR") {
          /* reached without an at-bat in this count */
        } else {
          row.ab += 1;
        }
      });
    });
    return {
      rows: Object.keys(rows).map(function (key) { return rows[key]; }).sort(function (a, b) {
        return b.pa - a.pa || a.batter.localeCompare(b.batter);
      }),
      skipped: skipped,
      named: named
    };
  }

  function workloadRows() {
    var previous = {};
    var rows = [];
    state.data.games.forEach(function (game, index) {
      game.pitching.forEach(function (line) {
        var key = line.team + "|" + line.player_id;
        var prior = previous[key];
        var rest = "first appearance";
        if (prior) {
          if (!prior.game.date || !game.date) rest = "date not recorded";
          else rest = String(Math.round((Date.parse(game.date + "T00:00:00Z") - Date.parse(prior.game.date + "T00:00:00Z")) / 86400000));
        }
        var fatigue = (game.fatigue_end_states || {})[key];
        var fatigueText = "not recorded";
        if (fatigue) {
          fatigueText = fatigue.book_fatigued ? "book fatigued" : "not fatigued";
          if (fatigue.trigger) fatigueText += " (" + fatigue.trigger + ")";
        }
        var pitches = line.pitches != null ? line.pitches : (line.pc != null ? line.pc : null);
        rows.push({
          game: game, line: line, index: index, rest: rest, fatigue: fatigueText,
          pitches: pitches == null ? "—" : String(pitches)
        });
        previous[key] = { game: game };
      });
    });
    return rows;
  }

  function teamSplits() {
    var table = {};
    function row(code) {
      if (!table[code]) table[code] = { home: [0, 0], away: [0, 0], extra: [0, 0], one: [0, 0] };
      return table[code];
    }
    function mark(pair, won) { pair[won ? 0 : 1] += 1; }
    state.data.games.forEach(function (game) {
      var innings = Math.max((game.line[game.away] || []).length, (game.line[game.home] || []).length);
      var one = Math.abs(game.score[game.home] - game.score[game.away]) === 1;
      [game.home, game.away].forEach(function (code) {
        var bucket = row(code);
        var won = game.winner === code;
        mark(code === game.home ? bucket.home : bucket.away, won);
        if (innings > 9) mark(bucket.extra, won);
        if (one) mark(bucket.one, won);
      });
    });
    return table;
  }

  function recordPair(pair) {
    if (!pair || (pair[0] === 0 && pair[1] === 0)) return "—";
    return pair[0] + "-" + pair[1];
  }

  function headToHead() {
    var map = {};
    state.data.games.forEach(function (game) {
      var codes = [game.home, game.away].slice().sort();
      var id = codes[0] + "|" + codes[1];
      if (!map[id]) map[id] = { a: codes[0], b: codes[1], wins: {} };
      map[id].wins[game.winner] = (map[id].wins[game.winner] || 0) + 1;
    });
    state.data.series.forEach(function (series) {
      if (!series.team_a || !series.team_b || series.status !== "complete") return;
      var codes = [series.team_a, series.team_b].slice().sort();
      var id = codes[0] + "|" + codes[1];
      if (!map[id]) map[id] = { a: codes[0], b: codes[1], wins: {} };
      map[id].series = series;
    });
    return Object.keys(map).map(function (id) { return map[id]; }).sort(function (a, b) {
      return a.a.localeCompare(b.a) || a.b.localeCompare(b.b);
    });
  }

  function isWalkOff(game) {
    if (game.winner !== game.home) return false;
    var home = game.line[game.home] || [];
    var away = game.line[game.away] || [];
    if (!home.length || home[home.length - 1] <= 0) return false;
    var before = home.slice(0, -1).reduce(function (sum, runs) { return sum + runs; }, 0);
    var awayTotal = away.reduce(function (sum, runs) { return sum + runs; }, 0);
    return before <= awayTotal;
  }

  function renderStats() {
    markNav("stats");
    var page = el("article", { class: "stack" });
    page.appendChild(el("h2", { text: "Stats" }));
    page.appendChild(el("p", { class: "note", text: "Counted from the stored games, in archive order. A hit streak is consecutive games with a hit. A cold streak is consecutive games with none. Rest is the number of calendar days since that pitcher's previous appearance. Pitch counts appear only when a box score carries them; otherwise the line is innings and batters faced." }));
    var streakRows = [];
    Object.keys(state.players).forEach(function (key) {
      var player = state.players[key];
      var streak = hitStreak(player);
      if (streak.longestHit < 2 && streak.currentCold < 2) return;
      streakRows.push([
        linkPlayer(player.team, player.id, player.name),
        clubName(player.team),
        String(streak.currentHit),
        String(streak.longestHit),
        String(streak.currentCold),
        String(streak.longestCold)
      ]);
    });
    streakRows.sort(function (a, b) { return Number(b[3]) - Number(a[3]) || a[0].textContent.localeCompare(b[0].textContent); });
    page.appendChild(el("h3", { text: "Hot and cold" }));
    if (!streakRows.length) page.appendChild(el("p", { text: "No streak of two games yet." }));
    else page.appendChild(table(["Player", "Team", "Hit streak", "Longest", "Cold", "Longest cold"], streakRows));
    var loads = workloadRows();
    page.appendChild(el("h3", { text: "Pitcher workload" }));
    page.appendChild(table(
      ["Player", "Game", "IP", "BF", "Pitches", "Rest", "Fatigue"],
      loads.map(function (item) {
        return [
          linkPlayer(item.line.team, item.line.player_id, item.line.name),
          linkGame(item.game.id),
          ipLabel(nz(item.line.outs)),
          item.line.bf == null ? "—" : String(item.line.bf),
          item.pitches,
          item.rest,
          item.fatigue
        ];
      })
    ));
    page.appendChild(el("h3", { text: "Head to head" }));
    var pairs = headToHead();
    if (!pairs.length) page.appendChild(el("p", { text: "No two clubs have played." }));
    else {
      page.appendChild(table(["Clubs", "Games", "Series"], pairs.map(function (pair) {
        var clubs = el("span");
        clubs.appendChild(linkTeam(pair.a));
        clubs.appendChild(document.createTextNode(" and "));
        clubs.appendChild(linkTeam(pair.b));
        var seriesText = "—";
        if (pair.series) {
          var series = pair.series;
          seriesText = clubName(series.winner) + " " + series.wins[series.winner] + "-" + series.wins[series.loser];
        }
        return [clubs, (pair.wins[pair.a] || 0) + "-" + (pair.wins[pair.b] || 0), seriesText];
      })));
    }
    page.appendChild(el("h3", { text: "Team splits" }));
    var splits = teamSplits();
    var splitRows = state.data.teams.filter(function (team) { return team.game_wins + team.game_losses > 0; }).map(function (team) {
      var row = splits[team.code] || { home: [0, 0], away: [0, 0], extra: [0, 0], one: [0, 0] };
      return [linkTeam(team.code, team.name), recordPair(row.home), recordPair(row.away), recordPair(row.extra), recordPair(row.one)];
    });
    page.appendChild(table(["Team", "Home", "Away", "Extra innings", "One-run"], splitRows));
    page.appendChild(el("h3", { text: "Batter vs pitcher" }));
    var host = el("div");
    host.appendChild(el("p", { class: "muted", text: "Loading play logs…" }));
    page.appendChild(host);
    clear(view);
    view.appendChild(page);
    ensureDetails(function () {
      clear(host);
      var found = matchupRows();
      host.appendChild(el("p", { class: "note", text: "A plate appearance is matched only when the roll log names the batter and one pitcher recorded every out in that inning. " + found.named + " game logs name the batter. " + found.skipped + " plate appearances were in a shared inning and are not in the table. Roll logs that do not name the batter are omitted." }));
      if (!found.rows.length) {
        host.appendChild(el("p", { text: "No batter-pitcher plate appearance could be matched." }));
        return;
      }
      host.appendChild(table(
        ["Batter", "Pitcher", "PA", "AB", "H", "HR", "BB", "SO"],
        found.rows.slice(0, 40).map(function (row) {
          return [
            linkPlayer(row.batterTeam, row.batterId, row.batter),
            linkPlayer(row.pitcherTeam, row.pitcherId, row.pitcher),
            row.pa, row.ab, row.h, row.hr, row.bb, row.k
          ];
        })
      ));
    });
  }

  function changelogEvents(text) {
    return text.split(/\n(?=## )/).filter(function (block) { return block.indexOf("## ") === 0; }).map(function (block) {
      var lines = block.split("\n");
      var title = lines[0].replace(/^##\s+/, "");
      var body = lines.slice(1).join("\n").trim();
      var prose = "";
      body.split(/\n\n+/).some(function (part) {
        var trimmed = part.trim();
        if (!trimmed || trimmed.charAt(0) === "#") return false;
        prose = trimmed.replace(/\s+/g, " ");
        return true;
      });
      var dated = /^(\d{4}-\d{2}-\d{2})/.exec(title);
      return { date: dated ? dated[1] : "", title: title, text: prose };
    });
  }

  function fieldEvents() {
    var events = [];
    state.data.series.forEach(function (series) {
      if (series.status !== "complete" || !series.winner) return;
      var games = (series.games || []).map(function (id) { return state.games[id]; }).filter(Boolean);
      var dates = games.map(function (game) { return game.date; }).filter(Boolean).sort();
      events.push({
        date: dates.length ? dates[dates.length - 1] : "",
        order: series.id,
        kind: "Series",
        title: series.id + " final",
        text: clubName(series.winner) + " beat " + clubName(series.loser) + " " + series.wins[series.winner] + "-" + series.wins[series.loser] + (series.mvp ? ". MVP " + series.mvp.name + "." : "."),
        href: "#/series/" + series.id,
        label: series.id
      });
    });
    var found = milestones();
    found.nohitters.forEach(function (item) {
      events.push({
        date: item.game.date || "",
        order: item.game.id + "-nh",
        kind: "Milestone",
        title: item.line.name + " no-hitter",
        text: ipLabel(nz(item.line.outs)) + " IP, 0 H, " + nz(item.line.k) + " K in " + item.game.id + ".",
        href: "#/game/" + item.game.id,
        label: item.game.id
      });
    });
    found.highK.forEach(function (item) {
      events.push({
        date: item.game.date || "",
        order: item.game.id + "-k" + item.line.player_id,
        kind: "Milestone",
        title: item.line.name + " " + nz(item.line.k) + " strikeouts",
        text: nz(item.line.k) + " K in " + ipLabel(nz(item.line.outs)) + " IP, " + item.game.id + ".",
        href: "#/game/" + item.game.id,
        label: item.game.id
      });
    });
    state.data.games.forEach(function (game) {
      if (!isWalkOff(game)) return;
      var series = state.data.series.filter(function (item) { return item.id === game.series_id; })[0];
      var narrative = "";
      if (series && series.narratives) {
        series.narratives.forEach(function (item) {
          if (item.game === game.id && /walk-off/i.test(item.text || "")) narrative = item.text;
        });
      }
      events.push({
        date: game.date || "",
        order: game.id + "-wo",
        kind: "Milestone",
        title: clubName(game.home) + " walk-off",
        text: narrative || (clubName(game.home) + " won " + game.score[game.home] + "-" + game.score[game.away] + " on a walk-off in " + game.id + "."),
        href: "#/game/" + game.id,
        label: game.id
      });
    });
    return events;
  }

  function renderHistory() {
    markNav("history");
    var page = el("article", { class: "stack" });
    page.appendChild(el("h2", { text: "Tournament history" }));
    page.appendChild(el("p", { class: "note", text: "Series results and milestones are counted from the box scores. Rulings are the dated sections of CHANGELOG.md. A game with no stored date is listed after the dated items." }));
    var list = el("ol", { class: "timeline" });
    fieldEvents().sort(function (a, b) {
      if (!!a.date !== !!b.date) return a.date ? -1 : 1;
      if (a.date !== b.date) return a.date < b.date ? -1 : 1;
      return a.order < b.order ? -1 : 1;
    }).forEach(function (item) {
      list.appendChild(el("li", null,
        el("p", { class: "meta", text: (item.date || "Date not stored") + " · " + item.kind }),
        el("p", null, el("a", { href: item.href, text: item.title })),
        el("p", { text: item.text })
      ));
    });
    page.appendChild(el("h3", { text: "On the field" }));
    page.appendChild(list);
    page.appendChild(el("h3", { text: "Rulings" }));
    var rulings = el("div", { class: "stack" });
    rulings.appendChild(el("p", { class: "muted", text: "Loading the changelog…" }));
    page.appendChild(rulings);
    clear(view);
    view.appendChild(page);
    fetch("CHANGELOG.md").then(function (response) {
      if (!response.ok) throw new Error("changelog");
      return response.text();
    }).then(function (text) {
      clear(rulings);
      var items = el("ol", { class: "timeline" });
      changelogEvents(text).forEach(function (item) {
        items.appendChild(el("li", null,
          el("p", { class: "meta", text: item.date || "Undated" }),
          el("p", null, el("strong", { text: item.title })),
          item.text ? el("p", { text: item.text }) : el("p", { class: "muted", text: "See CHANGELOG.md." })
        ));
      });
      rulings.appendChild(items);
      rulings.appendChild(el("p", null, el("a", { href: "CHANGELOG.md", text: "Open the changelog" })));
    }).catch(function () {
      clear(rulings);
      rulings.appendChild(el("p", { text: "The changelog did not load." }));
    });
  }

  function ensureDetails(done) {
    var pending = state.data.games.filter(function (game) { return !detailCache[game.id]; });
    if (!pending.length) {
      done();
      return;
    }
    var left = pending.length;
    pending.forEach(function (game) {
      fetch(game.detail || ("games/" + game.id + ".json")).then(function (response) {
        if (!response.ok) throw new Error(game.id);
        return response.json();
      }).then(function (detail) {
        detailCache[game.id] = detail;
      }).catch(function () {
        detailCache[game.id] = { rolls: [] };
      }).then(function () {
        left -= 1;
        if (!left) done();
      });
    });
  }

  function renderRecap() {
    markNav("recap");
    var page = el("article", { class: "panel" });
    var doc = state.recap;
    if (!doc) {
      page.appendChild(el("h2", { text: "Weekly recap" }));
      page.appendChild(el("p", { text: "The recap feed has not been generated yet." }));
      clear(view);
      view.appendChild(page);
      return;
    }
    page.appendChild(el("h2", { text: doc.title || "Weekly recap" }));
    page.appendChild(el("p", { class: "meta", text: (doc.start || "") + " through " + (doc.end || "") }));
    page.appendChild(el("p", null, el("a", { href: "recap/" + doc.id + ".html", text: "Standalone recap page" })));
    if (!doc.games || !doc.games.length) page.appendChild(el("p", { text: "No dated games fall in this week." }));
    (doc.games || []).forEach(function (game) {
      page.appendChild(el("h3", null, linkGame(game.id)));
      page.appendChild(el("p", { text: game.away_name + " " + game.away_runs + ", " + game.home_name + " " + game.home_runs + "." }));
      if (game.recap) page.appendChild(el("p", { text: game.recap }));
    });
    if (doc.undated && doc.undated.length) {
      page.appendChild(el("h3", { text: "Undated games" }));
      page.appendChild(el("p", { text: "These games are on the book and have no calendar date, so they are not counted in the week: " + doc.undated.join(", ") + "." }));
    }
    var notes = [];
    var marks = doc.milestones || {};
    (marks.nohitters || []).forEach(function (item) { notes.push(item.name + " no-hitter in " + item.game); });
    (marks.high_k || []).forEach(function (item) { notes.push(item.name + " " + item.k + " strikeouts in " + item.game); });
    if (notes.length) {
      page.appendChild(el("h3", { text: "Milestones on the book" }));
      var list = el("ul");
      notes.forEach(function (note) { list.appendChild(el("li", { text: note })); });
      page.appendChild(list);
    }
    clear(view);
    view.appendChild(page);
  }

  function parseInnings(text, label, problems) {
    if (!String(text || "").trim()) {
      problems.push(label + " line score is empty.");
      return [];
    }
    var parts = String(text).split(",");
    var innings = [];
    parts.forEach(function (part, index) {
      var piece = part.trim();
      if (piece === "") return;
      if (!/^\d+$/.test(piece)) problems.push(label + " inning " + (index + 1) + " is not a whole number.");
      innings.push(parseInt(piece, 10) || 0);
    });
    return innings;
  }

  function parseIpOuts(text) {
    var value = String(text || "").trim();
    if (!value) return 0;
    if (value.indexOf(".") !== -1) {
      var bits = value.split(".");
      return (parseInt(bits[0], 10) || 0) * 3 + (parseInt((bits[1] || "0").slice(0, 1), 10) || 0);
    }
    return Math.round(parseFloat(value) * 3) || 0;
  }

  function slugId(name) {
    var letters = String(name || "").toLowerCase().replace(/[^a-z]/g, "");
    return (letters.slice(0, 8) || "player") + "01";
  }

  function splitCsv(line) {
    return String(line).split(",").map(function (part) { return part.trim(); });
  }

  function buildGameDraft(fields) {
    var problems = [];
    var series = fields.series.trim();
    var gameNo = parseInt(fields.game, 10);
    if (!/^[A-Za-z0-9]+-\d+$/.test(series)) problems.push("Series id should look like R1-04.");
    if (!gameNo || gameNo < 1) problems.push("Game number must be 1 or more.");
    var away = fields.away.trim().toUpperCase();
    var home = fields.home.trim().toUpperCase();
    if (!/^[A-Z]{2,3}$/.test(away) || !/^[A-Z]{2,3}$/.test(home) || away === home) {
      problems.push("Away and home need distinct club codes.");
    }
    if (fields.date && !/^\d{4}-\d{2}-\d{2}$/.test(fields.date.trim())) problems.push("Date must be YYYY-MM-DD or blank.");
    var id = series + "-G" + (gameNo || 0);
    var awayLine = parseInnings(fields.awayLine, away || "Away", problems);
    var homeLine = parseInnings(fields.homeLine, home || "Home", problems);
    var score = {};
    score[away] = awayLine.reduce(function (sum, runs) { return sum + runs; }, 0);
    score[home] = homeLine.reduce(function (sum, runs) { return sum + runs; }, 0);
    if (awayLine.length && homeLine.length && score[away] === score[home]) problems.push("The score is tied. A tournament game needs a winner.");
    var batting = [];
    var batByTeam = {};
    String(fields.batting || "").split("\n").forEach(function (raw) {
      if (!raw.trim()) return;
      var cols = splitCsv(raw);
      if (cols.length < 9) {
        problems.push("Batting row needs TEAM, Name, AB, R, H, HR, RBI, BB, SO: " + raw.trim());
        return;
      }
      var team = cols[0].toUpperCase();
      if (team !== away && team !== home) problems.push("Batting team " + team + " is not in this game.");
      batByTeam[team] = (batByTeam[team] || 0) + 1;
      batting.push({
        team: team,
        player_id: slugId(cols[1]),
        name: cols[1],
        lineup_slot: batByTeam[team],
        entry_order: 1,
        is_substitute: false,
        ab: numField(cols[2]),
        r: numField(cols[3]),
        h: numField(cols[4]),
        hr: numField(cols[5]),
        rbi: numField(cols[6]),
        bb: numField(cols[7]),
        k: numField(cols[8]),
        hbp: 0, sb: 0, cs: 0, sac: 0, sf: null, gidp: 0, ibb: null, doubles: 0, triples: 0
      });
    });
    var pitching = [];
    var pitByTeam = {};
    String(fields.pitching || "").split("\n").forEach(function (raw) {
      if (!raw.trim()) return;
      var cols = splitCsv(raw);
      if (cols.length < 8) {
        problems.push("Pitching row needs TEAM, Name, IP, H, R, ER, BB, SO: " + raw.trim());
        return;
      }
      var team = cols[0].toUpperCase();
      if (team !== away && team !== home) problems.push("Pitching team " + team + " is not in this game.");
      pitByTeam[team] = (pitByTeam[team] || 0) + 1;
      pitching.push({
        team: team,
        player_id: slugId(cols[1]),
        name: cols[1],
        appearance_order: pitByTeam[team],
        outs: parseIpOuts(cols[2]),
        h: numField(cols[3]),
        r: numField(cols[4]),
        er: numField(cols[5]),
        bb: numField(cols[6]),
        k: numField(cols[7]),
        bf: 0,
        hb: null,
        hr: null
      });
    });
    if (!batting.length) problems.push("Add at least one batting row.");
    [away, home].forEach(function (code) {
      if (!code) return;
      var runs = batting.filter(function (line) { return line.team === code; }).reduce(function (sum, line) { return sum + line.r; }, 0);
      if (batting.some(function (line) { return line.team === code; }) && runs !== score[code]) {
        problems.push(code + " batting runs " + runs + " do not match the line score " + score[code] + ".");
      }
      if (batting.length && !batting.some(function (line) { return line.team === code; })) problems.push("No batting line for " + code + ".");
    });
    if (pitching.length) {
      [away, home].forEach(function (code) {
        var other = code === away ? home : away;
        var allowed = pitching.filter(function (line) { return line.team === code; }).reduce(function (sum, line) { return sum + line.r; }, 0);
        if (pitching.some(function (line) { return line.team === code; }) && allowed !== score[other]) {
          problems.push(code + " pitching runs " + allowed + " do not match " + other + "'s score " + score[other] + ".");
        }
      });
    }
    var winner = score[away] > score[home] ? away : home;
    var loser = winner === away ? home : away;
    var names = {};
    names[away] = fields.awayName.trim() || away;
    names[home] = fields.homeName.trim() || home;
    var game = {
      id: id,
      series_id: series,
      game_in_series: gameNo || 0,
      date: fields.date.trim() || null,
      away: away,
      home: home,
      teams: names,
      score: score,
      line: {},
      winner: winner,
      wls: {
        W: { team: winner, player_id: "winner01", name: fields.winnerName.trim() || "Winner" },
        L: { team: loser, player_id: "loser01", name: fields.loserName.trim() || "Loser" },
        S: null
      },
      batting: batting,
      pitching: pitching,
      errors_by: [],
      team_errors: {},
      final_grades: {},
      game_recap: fields.recap.trim(),
      series_recap: "",
      rng_seed: parseInt(fields.rng, 10) || 0,
      detail: "games/" + id + ".json",
      scoring_plays: []
    };
    game.line[away] = awayLine;
    game.line[home] = homeLine;
    game.team_errors[away] = 0;
    game.team_errors[home] = 0;
    var detail = {
      id: id,
      series_id: series,
      game_in_series: gameNo || 0,
      rolls: [],
      manager_log: null
    };
    if (!Array.isArray(detail.rolls)) problems.push("Detail file needs a rolls array.");
    return { problems: problems, game: game, detail: detail };
  }

  function numField(value) {
    var text = String(value || "").trim();
    if (!text) return 0;
    var number = Number(text);
    return isFinite(number) ? number : 0;
  }

  function downloadJson(filename, obj) {
    var blob = new Blob([JSON.stringify(obj, null, 1) + "\n"], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var link = el("a", { href: url, download: filename });
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function copyText(text, button) {
    var done = function () { button.textContent = "Copied"; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () { done(); });
      return;
    }
    var area = el("textarea", { text: text });
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (err) { /* the textarea is still on the page */ }
    area.remove();
    done();
  }

  function renderAdd() {
    markNav("add");
    var page = el("article", { class: "panel" });
    page.appendChild(el("h2", { text: "Add a game" }));
    page.appendChild(el("p", { class: "note", text: "This form checks a game summary and a detail file in the browser, then downloads them. It does not write the archive. Review the JSON before any hand merge. See ADDING_GAMES.md." }));
    page.appendChild(el("p", null, el("a", { href: "ADDING_GAMES.md", text: "How to add a game" })));
    var form = el("form", { class: "add-form", id: "add-game-form" });
    function field(name, label, value, kind) {
      var input = el("input", { name: name, id: "add-" + name, value: value || "" });
      if (kind) input.setAttribute("inputmode", kind);
      return el("label", { text: label }, input);
    }
    var top = el("div", { class: "form-row" });
    top.appendChild(field("series", "Series id", "R1-04"));
    top.appendChild(field("game", "Game number", "1", "numeric"));
    top.appendChild(field("date", "Date", ""));
    top.appendChild(field("rng", "RNG seed", "0", "numeric"));
    form.appendChild(top);
    var clubs = el("div", { class: "form-row" });
    clubs.appendChild(field("away", "Away code", ""));
    clubs.appendChild(field("awayName", "Away name", ""));
    clubs.appendChild(field("home", "Home code", ""));
    clubs.appendChild(field("homeName", "Home name", ""));
    form.appendChild(clubs);
    var lines = el("div", { class: "form-row" });
    lines.appendChild(field("awayLine", "Away line score", "0,0,0,0,0,0,0,0,0"));
    lines.appendChild(field("homeLine", "Home line score", "0,0,0,0,0,0,0,0,0"));
    form.appendChild(lines);
    var decisions = el("div", { class: "form-row" });
    decisions.appendChild(field("winnerName", "Winning pitcher", ""));
    decisions.appendChild(field("loserName", "Losing pitcher", ""));
    form.appendChild(decisions);
    form.appendChild(el("label", { text: "Batting, one player per line: TEAM, Name, AB, R, H, HR, RBI, BB, SO" },
      el("textarea", { name: "batting", id: "add-batting" })));
    form.appendChild(el("label", { text: "Pitching, one pitcher per line: TEAM, Name, IP, H, R, ER, BB, SO" },
      el("textarea", { name: "pitching", id: "add-pitching" })));
    form.appendChild(el("label", { text: "Recap" }, el("textarea", { name: "recap", id: "add-recap" })));
    var actions = el("div", { class: "form-actions" });
    actions.appendChild(el("button", { type: "submit", text: "Check" }));
    var downloadGame = el("button", { type: "button", text: "Download summary", disabled: "disabled" });
    var downloadDetail = el("button", { type: "button", text: "Download detail", disabled: "disabled" });
    var copyGame = el("button", { type: "button", class: "copy-button", text: "Copy summary", disabled: "disabled" });
    var copyDetail = el("button", { type: "button", class: "copy-button", text: "Copy detail", disabled: "disabled" });
    actions.appendChild(downloadGame);
    actions.appendChild(downloadDetail);
    actions.appendChild(copyGame);
    actions.appendChild(copyDetail);
    form.appendChild(actions);
    var report = el("div");
    form.appendChild(report);
    var draft = null;
    function readFields() {
      var data = {};
      ["series", "game", "date", "rng", "away", "awayName", "home", "homeName", "awayLine", "homeLine", "winnerName", "loserName", "batting", "pitching", "recap"].forEach(function (name) {
        data[name] = (form.elements[name] && form.elements[name].value) || "";
      });
      return data;
    }
    function showDraft(next) {
      draft = next;
      clear(report);
      var list = el("ul", { class: "problems" });
      next.problems.forEach(function (problem) { list.appendChild(el("li", { text: problem })); });
      if (next.problems.length) {
        report.appendChild(el("p", { text: "Fix these before downloading." }));
        report.appendChild(list);
      } else {
        report.appendChild(el("p", { text: "Shape check passed for " + next.game.id + ". The files are not in the archive until you merge them by hand." }));
      }
      var ready = next.problems.length ? "disabled" : null;
      [downloadGame, downloadDetail, copyGame, copyDetail].forEach(function (button) {
        if (ready) button.setAttribute("disabled", "disabled");
        else button.removeAttribute("disabled");
      });
      report.appendChild(el("h3", { text: "Summary JSON" }));
      report.appendChild(el("textarea", { readonly: "readonly", text: JSON.stringify(next.game, null, 1) }));
      report.appendChild(el("h3", { text: "Detail JSON" }));
      report.appendChild(el("textarea", { readonly: "readonly", text: JSON.stringify(next.detail, null, 1) }));
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      showDraft(buildGameDraft(readFields()));
    });
    downloadGame.addEventListener("click", function () {
      if (draft && !draft.problems.length) downloadJson(draft.game.id + ".json", draft.game);
    });
    downloadDetail.addEventListener("click", function () {
      if (draft && !draft.problems.length) downloadJson(draft.game.id + ".detail.json", draft.detail);
    });
    copyGame.addEventListener("click", function () {
      if (draft && !draft.problems.length) copyText(JSON.stringify(draft.game, null, 1) + "\n", copyGame);
    });
    copyDetail.addEventListener("click", function () {
      if (draft && !draft.problems.length) copyText(JSON.stringify(draft.detail, null, 1) + "\n", copyDetail);
    });
    page.appendChild(form);
    clear(view);
    view.appendChild(page);
  }

  function loadOnDemand(kind, again) {
    clear(view);
    view.appendChild(el("p", { text: "Loading…" }));
    state._loads = state._loads || {};
    if (!state._loads[kind]) {
      var url = kind === "cards" ? "data/cards.json" : "data/peak162.json";
      state._loads[kind] = loadOptional(url).then(function (data) {
        if (kind === "cards") {
          state.cards = data || {};
          state.cardsLoaded = true;
        } else {
          state.peak = data || null;
          state.peakLoaded = true;
        }
      });
    }
    state._loads[kind].then(again);
  }

  function renderAbout() {
    markNav("about");
    clear(view);
    var page = el("article", { class: "panel" });
    page.appendChild(el("h2", { text: "About this tournament" }));
    page.appendChild(el("p", { text: "Thirty-two all-time franchise clubs play a double-elimination bracket. Every series is a best of 7. A club is eliminated on its second series loss. There are no byes. After the opening round, each stage is reseeded by original seed, highest survivor against lowest." }));
    page.appendChild(el("p", { text: "Six seeds are Joe's pins: New York Yankees 1, Philadelphia Athletics 17, Oakland Athletics 22, Montreal Expos 27, Washington Nationals 31, and Miami Marlins 32. The other clubs fill the remaining slots by Full 26 Index." }));
    page.appendChild(el("p", { text: "On the book: the Yankees beat the Marlins 4-0, the Giants beat the Nationals 4-1, Boston beat Tampa Bay 4-3, and Detroit beat Arizona 4-2. R1-01 was played in APBA and adopted. Later series are played in Payoff Pitch. A stored line is the result. This page does not change one." }));
    page.appendChild(el("p", { text: "Every club's roster is on its team page. Twenty-five clubs have an owner card. Converted Payoff Pitch cards exist for eleven clubs: ARI, BOS, CHC, COL, DET, MON, PHA, SF, STL, TB, and WSH. Where both exist, the owner card is the list and the converted set is under Payoff Pitch cards." }));
    page.appendChild(el("p", { class: "note", text: PEAK_NOTE }));
    view.appendChild(page);
  }

  function renderFormulas() {
    markNav("formulas");
    clear(view);
    var page = el("article", { class: "panel" });
    page.appendChild(el("h2", { text: "Formulas" }));
    page.appendChild(el("p", { class: "note", text: "These are display models. They do not change a box score, a series score, or a seed." }));
    page.appendChild(el("h3", { text: "Awards" }));
    page.appendChild(el("p", { text: "MVP, hitters: total bases + R + RBI + SB + 0.5×BB + 0.5×HBP − CS. Total bases = H + 2B + 2×3B + 3×HR." }));
    page.appendChild(el("p", { text: "Cy Young, pitchers with at least one start: IP + 0.4×K + 5×W − 1.5×ER − 0.3×BB. IP is outs / 3." }));
    page.appendChild(el("p", { text: "Reliever, pitchers with zero starts: 5×SV + 2×IP + 0.4×K − 1.5×ER. A pitcher who has started stays on the Cy Young list." }));
    page.appendChild(el("h3", { text: "Win probability" }));
    page.appendChild(el("p", { text: "Before the first pitch the home club is 0.50. After each step the home win probability is 1 / (1 + exp(−1.35 × margin / sqrt(innings left))). Margin is home runs minus away runs. Innings left is at least 0.5. The chart uses the stored line, and scoring plays only when they land on the final score. It is omitted when the innings do not add up to that score." }));
    page.appendChild(el("h3", { text: "Series odds" }));
    page.appendChild(el("p", { text: "Each remaining game is an independent 0.55 win for the higher seed. The bar is the chance that club reaches 4 wins first. A completed series shows the winner at 1." }));
    page.appendChild(el("p", { text: "The bracket also shows a Monte Carlo from the club indexes: one game is 1 / (1 + exp(−(index A − index B) / 80)), with no home-field edge. Four thousand draws use a fixed seed. A finished series is recorded as 1 and 0, not resimulated. A shown 0.0 means that side won none of the draws." }));
    page.appendChild(el("h3", { text: "Peak 162" }));
    page.appendChild(el("p", { text: PEAK_NOTE + " The label is Peak 162 with the club and the first and last year of the stretch." }));
    page.appendChild(el("h3", { text: "Run differential" }));
    page.appendChild(el("p", { text: "Run differential is runs scored minus runs allowed, summed from the game scores." }));
    view.appendChild(page);
  }

  function render() {
    if (!state.data) return;
    var where = route();
    var activeSeries = where.name === "series" ? where.rest[0] : (where.name === "game" && state.games[where.rest[0]] ? state.games[where.rest[0]].series_id : "");
    if (where.name === "standings") renderStandings();
    else if (where.name === "rosters") renderRosters();
    else if (where.name === "awards") renderAwards();
    else if (where.name === "records") renderRecords();
    else if (where.name === "series") renderSeries(where.rest[0]);
    else if (where.name === "game") renderGame(where.rest[0]);
    else if (where.name === "team") renderTeam(where.rest[0]);
    else if (where.name === "player") renderPlayer(where.rest[0], where.rest[1]);
    else if (where.name === "search") renderSearch(where.query || where.rest.join("/"));
    else if (where.name === "previews") renderPreviews();
    else if (where.name === "stats") renderStats();
    else if (where.name === "history") renderHistory();
    else if (where.name === "recap") renderRecap();
    else if (where.name === "add") renderAdd();
    else if (where.name === "about") renderAbout();
    else if (where.name === "formulas") renderFormulas();
    else renderBracket(activeSeries);
    renderBanner();
    if (where.name === "bracket" && activeSeries) {
      /* bracket already showing */
    }
    var played = state.data.games.length;
    var r103 = state.data.series.filter(function (series) { return series.id === "R1-03"; })[0];
    var r103Text = r103 && r103.status === "complete" ? "R1-03 is complete, Boston 4-3." : "R1-03 is in progress.";
    lede.textContent = played + " games on record. " + r103Text + " Open a series, a game, or a club.";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    storageSet("pp-theme", theme);
    themeButton.textContent = theme === "dark" ? "Light mode" : "Dark mode";
  }

  themeButton.addEventListener("click", function () {
    var current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    applyTheme(current === "dark" ? "light" : "dark");
  });
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light");

  function setMenu(open) {
    if (open) siteHeader.classList.add("menu-open");
    else siteHeader.classList.remove("menu-open");
    menuButton.setAttribute("aria-expanded", open ? "true" : "false");
    menuButton.textContent = open ? "Close" : "Menu";
  }

  menuButton.addEventListener("click", function () {
    setMenu(!siteHeader.classList.contains("menu-open"));
  });

  searchForm.addEventListener("submit", function (event) {
    event.preventDefault();
    location.hash = "#/search?q=" + encodeURIComponent(searchInput.value.trim());
  });

  window.addEventListener("hashchange", function () {
    if (window.matchMedia("(max-width: 720px)").matches) setMenu(false);
    var where = route();
    if (where.name === "search") searchInput.value = where.query || where.rest.join("/");
    render();
  });

  function loadOptional(url) {
    return fetch(url).then(function (response) {
      if (!response.ok) throw new Error(url);
      return response.json();
    }).catch(function () { return null; });
  }

  fetch("tournament_results.json").then(function (response) {
    if (!response.ok) throw new Error("tournament_results.json");
    return response.json();
  }).then(function (data) {
    return Promise.all([
      data,
      loadOptional("data/teams.json"),
      loadOptional("data/bios.json"),
      loadOptional("data/rosters.json"),
      loadOptional("feed/odds.json"),
      loadOptional("feed/recap.json"),
      loadOptional("data/announced_rosters.json")
    ]);
  }).then(function (parts) {
    var data = parts[0];
    state.data = data;
    state.colors = parts[1] || {};
    state.bios = parts[2] || {};
    state.rosters = parts[3] || {};
    state.odds = parts[4];
    state.recap = parts[5];
    state.announced = parts[6] || {};
    state.cards = {};
    state.cardsLoaded = false;
    state.peak = null;
    state.peakLoaded = false;
    state.highlight = storageGet("pp-path");
    data.teams.forEach(function (team) { state.byCode[team.code] = team; });
    data.games.forEach(function (game) { state.games[game.id] = game; });
    indexPlayers();
    renderNext();
    var complete = data.series.filter(function (series) { return series.status === "complete"; }).length;
    var progress = data.series.filter(function (series) { return series.status === "in-progress"; }).length;
    footer.textContent = data.teams.length + " clubs. " + complete + " series complete, " + progress + " in progress. Display formulas are on the Formulas page. Logo files live in data/teams.json: a 1986 file where the franchise matches, a monogram otherwise.";
    if (!location.hash) location.hash = "#/bracket";
    var where = route();
    if (where.name === "search") searchInput.value = where.query || where.rest.join("/");
    render();
  }).catch(function () {
    showError("The results file did not load. Serve this folder over HTTP. Opening the file directly cannot fetch JSON.");
  });
})();
