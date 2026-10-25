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

  var state = { data: null, byCode: {}, games: {}, players: {}, highlight: "" };
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

  function logo(team, label) {
    var color = placeholderColor(team.seed);
    var node = svg("svg", { class: "logo", viewBox: "0 0 64 64", role: "img" });
    node.appendChild(svg("title")).textContent = label || (team.code + " placeholder");
    node.appendChild(svg("rect", { width: "64", height: "64", rx: "8", fill: color }));
    var text = svg("text", {
      x: "32", y: "40", "text-anchor": "middle",
      "font-family": "Georgia, serif", "font-size": "18", fill: "#f6f1e6"
    });
    text.textContent = team.code;
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
    var parts = raw.split("/").filter(Boolean);
    if (!parts.length) parts = ["bracket"];
    return { name: parts[0], rest: parts.slice(1).map(decodeURIComponent) };
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

  function oddsFor(series) {
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
    return { high: high, low: low, pHigh: pHigh };
  }

  function oddsBar(series) {
    var odds = oddsFor(series);
    if (!odds) return null;
    var left = Math.round(odds.pHigh * 1000) / 10;
    var right = Math.round((1 - odds.pHigh) * 1000) / 10;
    var track = el("div", { class: "odds-track" });
    var a = el("span", { text: left.toFixed(1) + "%" });
    var b = el("span", { text: right.toFixed(1) + "%" });
    a.style.width = left + "%";
    b.style.width = right + "%";
    a.style.background = placeholderColor(state.byCode[odds.high] ? state.byCode[odds.high].seed : 1);
    b.style.background = placeholderColor(state.byCode[odds.low] ? state.byCode[odds.low].seed : 2);
    track.appendChild(a);
    track.appendChild(b);
    return el("div", { class: "odds" },
      el("p", { class: "muted", text: "Series odds, higher seed " + HIGHER_SEED_P + " each remaining game. A finished series shows the winner at 100%." }),
      el("p", null, linkTeam(odds.high), " " + left.toFixed(1) + "% · ", linkTeam(odds.low), " " + right.toFixed(1) + "%"),
      track
    );
  }

  function homeWp(margin, inning, bottom) {
    var inningsLeft = Math.max(0.5, 9.5 - inning - (bottom ? 0.5 : 0));
    var scale = WP_SCALE / Math.sqrt(inningsLeft);
    return 1 / (1 + Math.exp(-scale * margin));
  }

  function wpEvents(game) {
    var events = [];
    var fallback = false;
    var home = 0;
    var away = 0;
    var plays = game.scoring_plays || [];
    if (plays.length) {
      plays.forEach(function (text) {
        var inningMatch = /Inning\s+(\d+)/.exec(text);
        var inning = inningMatch ? parseInt(inningMatch[1], 10) : 1;
        var pair = /([A-Z]{2,3})\s+(\d+),\s*([A-Z]{2,3})\s+(\d+)/.exec(text);
        var nextHome = home;
        var nextAway = away;
        if (pair) {
          var map = {};
          map[pair[1]] = Number(pair[2]);
          map[pair[3]] = Number(pair[4]);
          if (map[game.home] == null || map[game.away] == null) return;
          nextHome = map[game.home];
          nextAway = map[game.away];
        } else {
          var tail = /(\d+)\s*-\s*(\d+)\s*$/.exec(text);
          if (!tail) return;
          nextHome = Number(tail[1]);
          nextAway = Number(tail[2]);
        }
        var bottom = nextHome > home;
        home = nextHome;
        away = nextAway;
        events.push({ inning: inning, bottom: bottom, home: home, away: away, text: text });
      });
    }
    if (!events.length) {
      fallback = true;
      var awayLine = game.line[game.away] || [];
      var homeLine = game.line[game.home] || [];
      var n = Math.max(awayLine.length, homeLine.length);
      home = 0;
      away = 0;
      for (var i = 0; i < n; i++) {
        var ar = awayLine[i] || 0;
        var r;
        for (r = 0; r < ar; r++) {
          away += 1;
          events.push({ inning: i + 1, bottom: false, home: home, away: away, text: "Line score, inning " + (i + 1) + " top" });
        }
        var hr = homeLine[i] || 0;
        for (r = 0; r < hr; r++) {
          home += 1;
          events.push({ inning: i + 1, bottom: true, home: home, away: away, text: "Line score, inning " + (i + 1) + " bottom" });
        }
      }
    }
    return { events: events, fallback: fallback };
  }

  function wpChart(game) {
    var parsed = wpEvents(game);
    var points = [{ label: "Start", p: 0.5, text: "Before the first run" }];
    parsed.events.forEach(function (event) {
      points.push({
        label: event.inning + (event.bottom ? " bottom" : " top"),
        p: homeWp(event.home - event.away, event.inning, event.bottom),
        text: event.text
      });
    });
    var width = 640;
    var height = 220;
    var pad = 28;
    var chart = svg("svg", { class: "chart", viewBox: "0 0 " + width + " " + height, role: "img" });
    chart.appendChild(svg("title")).textContent = "Home win probability";
    chart.appendChild(svg("line", { x1: pad, y1: pad, x2: pad, y2: height - pad, stroke: "#8a8175" }));
    chart.appendChild(svg("line", { x1: pad, y1: height - pad, x2: width - pad, y2: height - pad, stroke: "#8a8175" }));
    var mid = svg("line", {
      x1: pad, y1: pad + (height - 2 * pad) / 2,
      x2: width - pad, y2: pad + (height - 2 * pad) / 2,
      stroke: "#c6a15a", "stroke-dasharray": "4 4"
    });
    chart.appendChild(mid);
    var coords = points.map(function (point, index) {
      var x = pad + (points.length === 1 ? 0 : (index / (points.length - 1)) * (width - 2 * pad));
      var y = pad + (1 - point.p) * (height - 2 * pad);
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    chart.appendChild(svg("polyline", { points: coords, fill: "none", stroke: "#1d5c3d", "stroke-width": "2" }));
    var caption = parsed.fallback
      ? "Line-score fallback. This game has no scoring plays, so the curve steps through the line score."
      : "Each point is a scoring play. Home win probability uses the model in MODELS.md.";
    var list = el("ol", { class: "muted" });
    points.forEach(function (point) {
      list.appendChild(el("li", { text: point.label + ": home " + Math.round(point.p * 100) + "%. " + point.text }));
    });
    return el("div", null,
      el("h4", { text: "Win probability" }),
      chart,
      el("p", { class: "muted", text: caption }),
      el("details", null, el("summary", { text: "Probability after each run" }), list)
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
    return found;
  }

  function renderNext() {
    clear(nextUp);
    var upcoming = nextGame();
    if (!upcoming) {
      nextUp.appendChild(el("p", { text: "No series is in progress." }));
      return;
    }
    var homeStarter = upcoming.starters[upcoming.home] || "starter not named";
    var awayStarter = upcoming.starters[upcoming.away] || "starter not named";
    nextUp.appendChild(el("p", { class: "eyebrow", text: "Next up" }));
    var p = el("p");
    p.appendChild(el("a", {
      href: "#/series/" + upcoming.series.id,
      text: upcoming.series.id + " Game " + upcoming.number + " at " + clubName(upcoming.home)
    }));
    nextUp.appendChild(p);
    nextUp.appendChild(el("p", { text: awayStarter + " (" + upcoming.away + ") at " + homeStarter + " (" + upcoming.home + ")." }));
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
          pit: { outs: 0, h: 0, r: 0, er: 0, bb: 0, k: 0, gs: 0, w: 0, l: 0, sv: 0 },
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
        ["outs", "h", "r", "er", "bb", "k"].forEach(function (field) {
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
    return card;
  }

  function renderBracket(activeId) {
    markNav("bracket");
    var root = el("div");
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
    var graphic = "graphics/series/" + series.id + ".svg";
    if (series.status === "complete" || series.status === "in-progress") {
      var img = el("img", { class: "share-card", src: graphic, alt: series.id + " series score graphic" });
      page.appendChild(el("h4", { text: "Share" }));
      page.appendChild(el("p", null, img));
      page.appendChild(el("p", null, el("a", { href: graphic, text: "SVG" }), " · ", el("a", { href: "graphics/series/" + series.id + ".png", text: "PNG" })));
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
    page.appendChild(el("p", null, el("a", { href: "#/series/" + game.series_id, text: game.series_id })));
    page.appendChild(el("h2", { text: clubName(game.away) + " " + game.score[game.away] + " at " + clubName(game.home) + " " + game.score[game.home] }));
    page.appendChild(el("p", { class: "meta", text: game.id + (game.date ? " · " + game.date : "") + " · " + decisionText(game) }));
    page.appendChild(linescore(game));
    page.appendChild(boxTables(game));
    page.appendChild(el("h4", { text: "Scoring plays" }));
    if (game.scoring_plays && game.scoring_plays.length) {
      var list = el("ol");
      game.scoring_plays.forEach(function (play) { list.appendChild(el("li", { text: play })); });
      page.appendChild(list);
    } else {
      page.appendChild(el("p", { text: "No scoring plays were recorded." }));
    }
    page.appendChild(wpChart(game));
    page.appendChild(el("h4", { text: "Recap" }));
    page.appendChild(el("p", { class: "recap", text: game.game_recap || "No recap was stored." }));
    if (game.series_recap) page.appendChild(el("p", { class: "recap", text: game.series_recap }));
    var logHost = el("div");
    page.appendChild(el("h4", { text: "Manager log" }));
    page.appendChild(logHost);
    logHost.appendChild(el("p", { class: "muted", text: "Loading the game file…" }));
    var share = el("p", null,
      el("img", { class: "share-card", src: "graphics/games/" + game.id + ".svg", alt: game.id + " final score graphic" })
    );
    page.appendChild(el("h4", { text: "Share" }));
    page.appendChild(share);
    page.appendChild(el("p", null,
      el("a", { href: "graphics/games/" + game.id + ".svg", text: "SVG" }),
      " · ",
      el("a", { href: "graphics/games/" + game.id + ".png", text: "PNG" }),
      " · ",
      el("a", { href: "box_scores/" + game.id + ".md", text: "Box score markdown" })
    ));
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

  function renderTeam(code) {
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
    hero.appendChild(logo(team, team.name + " placeholder monogram"));
    hero.appendChild(el("div", null,
      el("h2", { text: "#" + team.seed + " " + team.name }),
      el("p", { class: "meta", text: team.code + " · " + (team.bracket || "winners") + " bracket · series " + team.series_wins + "-" + team.series_losses + " · games " + team.game_wins + "-" + team.game_losses })
    ));
    page.appendChild(hero);
    page.appendChild(el("p", { class: "muted", text: "Placeholder monogram and color. Not a club mark." }));
    page.appendChild(el("p", { text: "Run differential " + (diff.rs - diff.ra) + " (" + diff.rs + " scored, " + diff.ra + " allowed)." }));
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
    page.appendChild(el("h3", { text: "Roster stats" }));
    if (!batRows.length && !pitRows.length) page.appendChild(el("p", { text: "No appearances yet. Positions stay unrecorded until the club plays." }));
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

  function renderPlayer(code, id) {
    markNav("standings");
    var player = state.players[code + "|" + id];
    clear(view);
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
    if (paOf(player.bat) > 0) {
      page.appendChild(el("h3", { text: "Batting" }));
      page.appendChild(table(
        ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "SB", "AVG"],
        [[
          paOf(player.bat), player.bat.ab, player.bat.r, player.bat.h, player.bat.doubles, player.bat.triples,
          player.bat.hr, player.bat.rbi, player.bat.bb, player.bat.k, player.bat.sb,
          rateLabel(player.bat.h, player.bat.ab)
        ]]
      ));
    }
    if (player.pit.outs + player.pit.w + player.pit.l + player.pit.sv > 0) {
      page.appendChild(el("h3", { text: "Pitching" }));
      page.appendChild(table(
        ["GS", "W", "L", "SV", "IP", "H", "ER", "BB", "SO", "ERA"],
        [[player.pit.gs, player.pit.w, player.pit.l, player.pit.sv, ipLabel(player.pit.outs), player.pit.h, player.pit.er, player.pit.bb, player.pit.k, eraLabel(player.pit.er, player.pit.outs)]]
      ));
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
    markNav("standings");
    var needle = (query || "").trim().toLowerCase();
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
    }).sort(function (a, b) { return a.name.localeCompare(b.name) || a.team.localeCompare(b.team); });
    if (!hits.length) page.appendChild(el("p", { text: "No matching player line." }));
    hits.forEach(function (player) {
      page.appendChild(el("p", null, linkPlayer(player.team, player.id, player.name), " · ", linkTeam(player.team)));
    });
    view.appendChild(page);
  }

  function render() {
    if (!state.data) return;
    var where = route();
    var activeSeries = where.name === "series" ? where.rest[0] : (where.name === "game" && state.games[where.rest[0]] ? state.games[where.rest[0]].series_id : "");
    if (where.name === "standings") renderStandings();
    else if (where.name === "awards") renderAwards();
    else if (where.name === "records") renderRecords();
    else if (where.name === "series") renderSeries(where.rest[0]);
    else if (where.name === "game") renderGame(where.rest[0]);
    else if (where.name === "team") renderTeam(where.rest[0]);
    else if (where.name === "player") renderPlayer(where.rest[0], where.rest[1]);
    else if (where.name === "search") renderSearch(where.rest.join("/"));
    else renderBracket(activeSeries);
    if (where.name === "bracket" && activeSeries) {
      /* bracket already showing */
    }
    var played = state.data.games.length;
    lede.textContent = played + " games on record. R1-03 is in progress. Open a series, a game, or a club.";
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

  searchForm.addEventListener("submit", function (event) {
    event.preventDefault();
    location.hash = "#/search/" + encodeURIComponent(searchInput.value.trim());
  });

  window.addEventListener("hashchange", render);

  fetch("tournament_results.json").then(function (response) {
    if (!response.ok) throw new Error("tournament_results.json");
    return response.json();
  }).then(function (data) {
    state.data = data;
    state.highlight = storageGet("pp-path");
    data.teams.forEach(function (team) { state.byCode[team.code] = team; });
    data.games.forEach(function (game) { state.games[game.id] = game; });
    indexPlayers();
    renderNext();
    var complete = data.series.filter(function (series) { return series.status === "complete"; }).length;
    var progress = data.series.filter(function (series) { return series.status === "in-progress"; }).length;
    footer.textContent = data.teams.length + " clubs. " + complete + " series complete, " + progress + " in progress. Formulas are in MODELS.md. Placeholder colors are not club marks.";
    if (!location.hash) location.hash = "#/bracket";
    render();
  }).catch(function () {
    showError("The results file did not load. Serve this folder over HTTP. Opening the file directly cannot fetch JSON.");
  });
})();
