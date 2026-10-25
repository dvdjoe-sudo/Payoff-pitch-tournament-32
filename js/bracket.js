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
    { id: "losers", title: "Losers bracket", blurb: "A club enters here with one series loss. The next series loss eliminates it. Drop-in rounds reseed survivors together with the clubs that just lost." },
    { id: "finals", title: "Finals", blurb: "F-02 is stored as its own slot. Its gate says when it is played." }
  ];

  var STATUS = {
    complete: "Final",
    scheduled: "Scheduled",
    "awaiting-feeders": "Waiting"
  };

  var state = {
    data: null,
    byCode: {},
    games: {},
    selectedSeries: null,
    selectedGame: null,
    log: null
  };
  var detailCache = {};

  var bracketView = document.getElementById("bracket-view");
  var standingsView = document.getElementById("standings-view");
  var lede = document.getElementById("lede");
  var footer = document.getElementById("footer-note");
  var errorBox = document.getElementById("load-error");

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
      if (child == null) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  function seriesNumber(id) {
    var part = id.split("-").pop();
    var value = parseInt(part, 10);
    return isNaN(value) ? 0 : value;
  }

  function clubName(code) {
    if (!code) return "TBD";
    var team = state.byCode[code];
    return team ? team.name : code;
  }

  function seedOf(series, code) {
    if (code && code === series.team_a && series.seed_a != null) return series.seed_a;
    if (code && code === series.team_b && series.seed_b != null) return series.seed_b;
    return null;
  }

  function showError(message) {
    errorBox.hidden = false;
    errorBox.textContent = message;
    lede.textContent = "The bracket could not be loaded.";
  }

  function setView(name) {
    var bracket = name === "bracket";
    document.getElementById("tab-bracket").setAttribute("aria-selected", bracket ? "true" : "false");
    document.getElementById("tab-standings").setAttribute("aria-selected", bracket ? "false" : "true");
    bracketView.hidden = !bracket;
    standingsView.hidden = bracket;
  }

  function selectSeries(id, gameId) {
    state.selectedSeries = id;
    state.selectedGame = gameId || null;
    state.log = null;
    if (id) history.replaceState(null, "", "#" + id);
    renderBracket();
    var panel = document.getElementById("series-panel");
    if (panel) panel.scrollIntoView({ block: "nearest" });
  }

  function render() {
    var data = state.data;
    var complete = data.series.filter(function (series) { return series.status === "complete"; }).length;
    var eliminated = data.teams.filter(function (team) { return team.bracket === "eliminated" || team.eliminated; }).length;
    lede.textContent = data.teams.length + " clubs. Best of 7. Double elimination, reseeded at every stage after the opening round. " +
      complete + " series complete, " + data.games.length + " games on record, " + eliminated + " clubs eliminated.";
    footer.textContent = "Schema version " + data.schema_version + ". Drawn from tournament_results.json. Pairings after Round 1 appear when that stage's feeders are complete.";
    renderStandings();
    var hash = decodeURIComponent(location.hash.replace(/^#/, ""));
    var initial = data.series.some(function (series) { return series.id === hash; }) ? hash : "R1-02";
    state.selectedSeries = initial;
    renderBracket();
  }

  function renderStandings() {
    standingsView.replaceChildren();
    var table = el("table", { class: "standings" });
    var head = el("tr");
    ["Seed", "Team", "Bracket", "Series", "Games"].forEach(function (label, index) {
      head.appendChild(el("th", { text: label, class: index >= 3 ? "num" : null, scope: "col" }));
    });
    table.appendChild(el("thead", null, head));
    var body = el("tbody");
    state.data.teams.slice().sort(function (a, b) { return a.seed - b.seed; }).forEach(function (team) {
      var bracket = team.bracket || "winners";
      var row = el("tr", { class: bracket });
      row.appendChild(el("td", { text: String(team.seed), class: "num" }));
      row.appendChild(el("td", { text: team.name }));
      row.appendChild(el("td", { text: bracket.charAt(0).toUpperCase() + bracket.slice(1) }));
      row.appendChild(el("td", { text: team.series_wins + "-" + team.series_losses, class: "num" }));
      row.appendChild(el("td", { text: team.game_wins + "-" + team.game_losses, class: "num" }));
      body.appendChild(row);
    });
    table.appendChild(body);
    standingsView.appendChild(el("h2", { text: "Standings" }));
    standingsView.appendChild(el("p", {
      class: "note",
      text: "Series losses are the elimination counter: none keeps a club in the winners bracket, one moves it to the losers bracket, two eliminates it. Six seeds are Joe's pins rather than index order: Yankees, Philadelphia Athletics, Oakland, Montreal, Washington, and Miami. The seed table is TOURNAMENT_SEEDS.md."
    }));
    standingsView.appendChild(el("div", { class: "table-wrap" }, table));
  }

  function refreshPanel() {
    var existing = document.getElementById("series-panel");
    var next = renderPanel();
    if (existing) existing.replaceWith(next);
    else bracketView.appendChild(next);
  }

  function renderBracket() {
    bracketView.replaceChildren();
    GROUPS.forEach(function (group) {
      var section = el("section", { class: "group " + group.id });
      section.appendChild(el("h2", { text: group.title }));
      section.appendChild(el("p", { class: "note", text: group.blurb }));
      var scroller = el("div", { class: "scroller" });
      STAGES.filter(function (stage) { return stage.group === group.id; }).forEach(function (stage) {
        var seriesList = state.data.series.filter(function (series) { return stage.test(series.id); });
        seriesList.sort(function (a, b) { return seriesNumber(a.id) - seriesNumber(b.id); });
        var column = el("div", { class: "round" });
        column.appendChild(el("h3", { text: stage.title }));
        seriesList.forEach(function (series) { column.appendChild(seriesCard(series)); });
        scroller.appendChild(column);
      });
      section.appendChild(scroller);
      bracketView.appendChild(section);
    });
    bracketView.appendChild(renderPanel());
  }

  function seriesCard(series) {
    var button = el("button", {
      type: "button",
      class: "series-card" + (series.id === state.selectedSeries ? " selected" : ""),
      "data-series": series.id,
      "aria-pressed": series.id === state.selectedSeries ? "true" : "false"
    });
    var idRow = el("span", { class: "series-id" });
    idRow.appendChild(el("span", { text: series.id }));
    idRow.appendChild(el("span", { text: STATUS[series.status] || series.status }));
    button.appendChild(idRow);
    button.appendChild(clubLine(series, series.team_a));
    button.appendChild(clubLine(series, series.team_b));
    button.addEventListener("click", function () { selectSeries(series.id); });
    return button;
  }

  function clubLine(series, code) {
    var line = el("span", { class: "club-line" });
    var seed = seedOf(series, code);
    var label = (seed != null ? "#" + seed + " " : "") + clubName(code);
    var name = series.winner && series.winner === code ? el("strong", { text: label }) : el("span", { text: label });
    var runs = "";
    if (code && series.wins && Object.prototype.hasOwnProperty.call(series.wins, code) && series.status !== "awaiting-feeders") {
      runs = String(series.wins[code]);
    }
    line.appendChild(name);
    line.appendChild(el("span", { class: "runs", text: runs }));
    return line;
  }

  function renderPanel() {
    var series = state.data.series.find(function (item) { return item.id === state.selectedSeries; });
    var panel = el("section", { class: "panel", id: "series-panel" });
    if (!series) {
      panel.appendChild(el("p", { text: "Select a series." }));
      return panel;
    }
    panel.appendChild(el("h3", { text: series.label || series.id }));
    panel.appendChild(el("p", { class: "meta", text: seriesMeta(series) }));
    if (series.formation) {
      var formation = series.formation;
      panel.appendChild(el("p", { text: "Pool: " + (formation.pool || "—") }));
      panel.appendChild(el("p", { text: "Gate: " + (formation.gate || "—") }));
    }
    if (series.provenance) {
      var details = el("details");
      details.appendChild(el("summary", { text: "How this series was recorded" }));
      details.appendChild(el("p", { text: series.provenance }));
      panel.appendChild(details);
    }
    var gameIds = series.games || [];
    if (!gameIds.length) {
      panel.appendChild(el("p", { text: series.status === "scheduled" ? "Paired, and not started." : "This series has no pairing yet." }));
      appendHomePattern(panel, series);
      return panel;
    }
    if (!state.selectedGame || gameIds.indexOf(state.selectedGame) === -1) state.selectedGame = gameIds[0];
    var row = el("div", { class: "game-row" });
    gameIds.forEach(function (id) {
      var game = state.games[id];
      var away = game ? game.score[game.away] : "";
      var home = game ? game.score[game.home] : "";
      var label = "G" + (game ? game.game_in_series : "") + "  " + away + "–" + home;
      var button = el("button", {
        type: "button",
        text: label,
        "data-game": id,
        "aria-pressed": id === state.selectedGame ? "true" : "false"
      });
      button.addEventListener("click", function () {
        state.selectedGame = id;
        state.log = null;
        refreshPanel();
      });
      row.appendChild(button);
    });
    panel.appendChild(row);
    var game = state.games[state.selectedGame];
    if (game) panel.appendChild(renderBox(game));
    return panel;
  }

  function seriesMeta(series) {
    var bits = [series.id, STATUS[series.status] || series.status];
    if (series.winner && series.wins) {
      var won = series.wins[series.winner];
      var lost = series.wins[series.loser];
      bits.push(clubName(series.winner) + " won " + won + "-" + lost);
    }
    return bits.join(" · ");
  }

  function appendHomePattern(panel, series) {
    var homes = series.home_by_game || {};
    var keys = Object.keys(homes);
    if (!keys.length) return;
    var text = keys.sort(function (a, b) { return Number(a) - Number(b); }).map(function (key) {
      return "G" + key + " " + clubName(homes[key]);
    }).join(", ");
    panel.appendChild(el("p", { text: "Home: " + text }));
  }

  function renderBox(game) {
    var wrap = el("div");
    var when = game.date ? " · " + game.date : "";
    wrap.appendChild(el("p", {
      class: "meta",
      text: clubName(game.away) + " " + game.score[game.away] + " at " + clubName(game.home) + " " + game.score[game.home] + when
    }));
    wrap.appendChild(lineScore(game));
    [game.away, game.home].forEach(function (code) {
      wrap.appendChild(el("h4", { text: clubName(code) }));
      wrap.appendChild(battingTable(game, code));
    });
    wrap.appendChild(el("h4", { text: "Pitching" }));
    wrap.appendChild(pitchingTable(game));
    wrap.appendChild(el("p", { text: decisions(game) }));
    if (game.game_recap) wrap.appendChild(el("p", { class: "recap", text: game.game_recap }));
    if (game.scoring_plays && game.scoring_plays.length) {
      var list = el("ul");
      game.scoring_plays.forEach(function (play) { list.appendChild(el("li", { text: play })); });
      wrap.appendChild(el("h4", { text: "Scoring" }));
      wrap.appendChild(list);
    }
    var actions = el("div", { class: "log-actions" });
    actions.appendChild(logButton("Play log", "rolls"));
    actions.appendChild(logButton("Manager log", "manager"));
    wrap.appendChild(actions);
    var host = el("div", { class: "log-host", id: "log-host" });
    if (state.log) host.appendChild(el("p", { text: "Loading…" }));
    wrap.appendChild(host);
    if (state.log) fillLog(game, host);
    return wrap;
  }

  function logButton(label, kind) {
    var button = el("button", { type: "button", text: label, "data-log": kind });
    button.addEventListener("click", function () {
      state.log = state.log === kind ? null : kind;
      refreshPanel();
    });
    return button;
  }

  function lineScore(game) {
    var away = game.line[game.away] || [];
    var home = game.line[game.home] || [];
    var innings = Math.max(away.length, home.length);
    var table = el("table");
    var head = el("tr");
    head.appendChild(el("th", { text: "", scope: "col" }));
    for (var i = 0; i < innings; i += 1) head.appendChild(el("th", { text: String(i + 1), class: "num", scope: "col" }));
    ["R", "H", "E"].forEach(function (label) { head.appendChild(el("th", { text: label, class: "num", scope: "col" })); });
    table.appendChild(el("thead", null, head));
    var body = el("tbody");
    body.appendChild(lineRow(game, game.away, away, innings, false));
    body.appendChild(lineRow(game, game.home, home, innings, true));
    table.appendChild(body);
    return el("div", { class: "table-wrap" }, table);
  }

  function lineRow(game, code, innings, total, isHome) {
    var row = el("tr");
    row.appendChild(el("th", { text: clubName(code), scope: "row" }));
    for (var i = 0; i < total; i += 1) {
      var cell = i < innings.length ? String(innings[i]) : (isHome ? "x" : "");
      row.appendChild(el("td", { text: cell, class: "num" }));
    }
    row.appendChild(el("td", { text: String(game.score[code]), class: "num" }));
    row.appendChild(el("td", { text: String(hitTotal(game, code)), class: "num" }));
    var errors = game.team_errors && game.team_errors[code] != null ? game.team_errors[code] : 0;
    row.appendChild(el("td", { text: String(errors), class: "num" }));
    return row;
  }

  function hitTotal(game, code) {
    return game.batting.reduce(function (sum, line) {
      return sum + (line.team === code ? (line.h || 0) : 0);
    }, 0);
  }

  function stat(value) {
    return value == null ? "–" : String(value);
  }

  function battingTable(game, code) {
    var lines = game.batting.filter(function (line) { return line.team === code; });
    lines.sort(function (a, b) {
      return (a.lineup_slot || 99) - (b.lineup_slot || 99) || (a.entry_order || 99) - (b.entry_order || 99);
    });
    var columns = ["Player", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "K", "SB"];
    var table = el("table");
    var head = el("tr");
    columns.forEach(function (label, index) {
      head.appendChild(el("th", { text: label, class: index ? "num" : null, scope: "col" }));
    });
    table.appendChild(el("thead", null, head));
    var body = el("tbody");
    lines.forEach(function (line) {
      var row = el("tr", { class: line.is_substitute ? "sub" : null });
      var name = line.name + (line.is_substitute ? " (sub)" : "");
      row.appendChild(el("th", { text: name, scope: "row" }));
      [line.ab, line.r, line.h, line.doubles, line.triples, line.hr, line.rbi, line.bb, line.k, line.sb].forEach(function (value) {
        row.appendChild(el("td", { text: stat(value), class: "num" }));
      });
      body.appendChild(row);
    });
    table.appendChild(body);
    return el("div", { class: "table-wrap" }, table);
  }

  function decisionFor(game, line) {
    var wls = game.wls || {};
    var labels = ["W", "L", "S"];
    for (var i = 0; i < labels.length; i += 1) {
      var decision = wls[labels[i]];
      if (decision && decision.player_id === line.player_id && decision.team === line.team) return labels[i];
    }
    return "";
  }

  function pitchingTable(game) {
    var showHr = game.pitching.some(function (line) { return Object.prototype.hasOwnProperty.call(line, "hr"); });
    var table = el("table");
    var head = el("tr");
    var columns = ["Player", "IP", "H", "R", "ER", "BB", "K"];
    if (showHr) columns.push("HR");
    columns.push("DEC");
    columns.forEach(function (label, index) {
      head.appendChild(el("th", { text: label, class: index ? "num" : null, scope: "col" }));
    });
    table.appendChild(el("thead", null, head));
    var body = el("tbody");
    game.pitching.slice().sort(function (a, b) {
      if (a.team === b.team) return a.appearance_order - b.appearance_order;
      if (a.team === game.away) return -1;
      if (b.team === game.away) return 1;
      return 0;
    }).forEach(function (line) {
      var row = el("tr");
      row.appendChild(el("th", { text: line.name + " (" + line.team + ")", scope: "row" }));
      [ipLabel(line.outs), stat(line.h), stat(line.r), stat(line.er), stat(line.bb), stat(line.k)].forEach(function (value) {
        row.appendChild(el("td", { text: value, class: "num" }));
      });
      if (showHr) row.appendChild(el("td", { text: stat(line.hr), class: "num" }));
      row.appendChild(el("td", { text: decisionFor(game, line), class: "num" }));
      body.appendChild(row);
    });
    table.appendChild(body);
    return el("div", { class: "table-wrap" }, table);
  }

  function ipLabel(outs) {
    var value = outs || 0;
    return Math.floor(value / 3) + "." + (value % 3);
  }

  function decisions(game) {
    var wls = game.wls || {};
    return ["W", "L", "S"].map(function (label) {
      var decision = wls[label];
      if (!decision) return label === "S" ? null : label + ": —";
      return label + ": " + decision.name + " (" + decision.team + ")";
    }).filter(Boolean).join("  ·  ");
  }

  function fillLog(game, host) {
    loadDetail(game).then(function (detail) {
      host.replaceChildren();
      if (state.log === "rolls") renderRolls(detail.rolls, host);
      else renderManager(detail.manager_log, host);
    }).catch(function (error) {
      host.replaceChildren(el("p", { text: "The play log could not be loaded. " + error.message }));
    });
  }

  function loadDetail(game) {
    if (game.rolls || game.manager_log) return Promise.resolve(game);
    if (detailCache[game.id]) return Promise.resolve(detailCache[game.id]);
    if (!game.detail) return Promise.reject(new Error("This game has no detail file."));
    return fetch(game.detail).then(function (response) {
      if (!response.ok) throw new Error(response.status + " " + response.statusText);
      return response.json();
    }).then(function (detail) {
      detailCache[game.id] = detail;
      return detail;
    });
  }

  function renderRolls(rolls, host) {
    if (!rolls || !rolls.length) {
      host.appendChild(el("p", { text: "No rolls were recorded for this game." }));
      return;
    }
    var table = el("table");
    var head = el("tr");
    if (Array.isArray(rolls[0])) {
      ["#", "Card", "Purpose"].forEach(function (label) { head.appendChild(el("th", { text: label, scope: "col" })); });
      table.appendChild(el("thead", null, head));
      var body = el("tbody");
      rolls.forEach(function (roll, index) {
        var row = el("tr");
        row.appendChild(el("td", { text: String(index + 1), class: "num" }));
        row.appendChild(el("td", { text: roll && roll.length ? String(roll[0]) : "" }));
        row.appendChild(el("td", { text: roll && roll.length > 1 ? String(roll[1]) : "" }));
        body.appendChild(row);
      });
      table.appendChild(body);
    } else {
      ["Inn", "Batter", "Roll", "Result"].forEach(function (label) { head.appendChild(el("th", { text: label, scope: "col" })); });
      table.appendChild(el("thead", null, head));
      var apba = el("tbody");
      rolls.forEach(function (roll) {
        var row = el("tr");
        var inning = roll.inning != null ? String(roll.inning) + (roll.half ? " " + roll.half : "") : "";
        row.appendChild(el("td", { text: inning }));
        row.appendChild(el("td", { text: roll.batter || "" }));
        row.appendChild(el("td", { text: roll.roll != null ? String(roll.roll) : "", class: "num" }));
        row.appendChild(el("td", { text: roll.result_text || "" }));
        apba.appendChild(row);
      });
      table.appendChild(apba);
    }
    host.appendChild(el("div", { class: "table-wrap" }, table));
  }

  function renderManager(log, host) {
    if (!log || !log.length) {
      host.appendChild(el("p", { text: "No manager log was recorded for this game." }));
      return;
    }
    var list = el("ul");
    log.forEach(function (line) { list.appendChild(el("li", { text: line })); });
    host.appendChild(list);
  }

  document.getElementById("tab-bracket").addEventListener("click", function () { setView("bracket"); });
  document.getElementById("tab-standings").addEventListener("click", function () { setView("standings"); });

  fetch("tournament_results.json").then(function (response) {
    if (!response.ok) throw new Error(response.status + " " + response.statusText);
    return response.json();
  }).then(function (data) {
    state.data = data;
    data.teams.forEach(function (team) { state.byCode[team.code] = team; });
    data.games.forEach(function (game) { state.games[game.id] = game; });
    render();
  }).catch(function (error) {
    showError("This page reads tournament_results.json from the same folder. Serve the repository root and open the site from there: python3 -m http.server 8000, then visit http://localhost:8000/. Opening the file directly will not load the JSON. (" + error.message + ")");
  });
})();
