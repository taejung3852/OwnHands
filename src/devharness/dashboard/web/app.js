/* OwnHands Dashboard v1 client.
 *
 * Read-only by construction: the only request that is not a GET is the
 * presentation ensure POST, and it is sent for exactly two real view intents.
 * Every string that came from a record is placed with textContent, so nothing
 * a record contains can become markup.
 */
"use strict";

var API = "/api/dashboard/v1";
var CHUNK_LABEL = 64;

var csrf = null;              /* memory only: never a cookie, never storage */
var routeToken = 0;           /* bumped per navigation, to drop late answers */
var inflight = new Set();     /* snapshot keys with an ensure in progress */
var asked = new Set();        /* snapshot keys already ensured this view */
var suspended = new Map();    /* polls paused while the tab was hidden */
var cooldown = new Map();     /* snapshot key -> epoch ms before a retry is allowed */
var polls = new Map();       /* snapshot key -> {timer, onDone, step, spent} */
var restoreClaim = null;     /* claim row to re-focus after the drawer closes */

function stamp(value) {
  if (!value) return "";
  return String(value).slice(0, 19).replace("T", " ");
}

/* ---------- tiny DOM helpers (no HTML parsing anywhere) ---------- */

function h(tag, props) {
  var node = document.createElement(tag);
  var options = props || {};
  Object.keys(options).forEach(function (name) {
    var value = options[name];
    if (value === null || value === undefined || value === false) return;
    if (name === "text") node.textContent = String(value);
    else if (name === "class") node.className = value;
    else if (name === "onclick") node.addEventListener("click", value);
    else if (name === "onkeydown") node.addEventListener("keydown", value);
    else if (name === "onsubmit") node.addEventListener("submit", value);
    else node.setAttribute(name, value === true ? "" : String(value));
  });
  for (var i = 2; i < arguments.length; i += 1) {
    var child = arguments[i];
    if (child === null || child === undefined || child === false) continue;
    if (Array.isArray(child)) child.forEach(function (one) { if (one) node.appendChild(one); });
    else if (typeof child === "string") node.appendChild(document.createTextNode(child));
    else node.appendChild(child);
  }
  return node;
}

var MARKS = {
  ready: ["M3 8.5 6.5 12 13 4"],
  needs: ["M8 2.6 14.6 13.4H1.4z", "M8 6.6v3", "M8 11.6h.01"],
  blocked: ["M4 12 12 4"],
  stale: ["M13.4 7a5.5 5.5 0 1 0-.7 4", "M13.6 2.8V7h-4.2"],
  unknown: [],
  chev: ["M6 3.5 10.5 8 6 12.5"],
  back: ["M10 3.5 5.5 8 10 12.5"],
  close: ["M4 4 12 12", "M12 4 4 12"],
  doc: ["M4 2.5h5l3 3v8H4z", "M9 2.5v3h3"],
  search: ["M10.6 10.6 14 14"]
};

function icon(name, size, stroke) {
  var ns = "http://www.w3.org/2000/svg";
  var svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", size || 16);
  svg.setAttribute("height", size || 16);
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", stroke || "currentColor");
  svg.setAttribute("stroke-width", "1.6");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  if (name === "blocked" || name === "unknown") {
    var circle = document.createElementNS(ns, "circle");
    circle.setAttribute("cx", "8"); circle.setAttribute("cy", "8"); circle.setAttribute("r", "6");
    if (name === "unknown") circle.setAttribute("stroke-dasharray", "2.2 2.4");
    svg.appendChild(circle);
  }
  if (name === "search") {
    var lens = document.createElementNS(ns, "circle");
    lens.setAttribute("cx", "7.2"); lens.setAttribute("cy", "7.2"); lens.setAttribute("r", "4.6");
    svg.appendChild(lens);
  }
  (MARKS[name] || []).forEach(function (d) {
    var path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  });
  return svg;
}

/* Review verdict, freshness and read health are separate axes and never merge. */
var VERDICT = {
  ready: { mark: "ready", word: "판단 가능", cls: "is-ready", stroke: "var(--ok-mark)" },
  "needs-review": { mark: "needs", word: "확인 필요", cls: "is-needs", stroke: "var(--warn-mark)" },
  blocked: { mark: "blocked", word: "검증 차단", cls: "is-blocked", stroke: "var(--danger-mark)" }
};

function verdictOf(card) {
  var base = VERDICT[card.review_state] || {
    mark: "unknown", word: card.state_label || "자료 확인 필요",
    cls: "is-unknown", stroke: "var(--stale-mark)"
  };
  if (card.review_state === "ready" && card.context && card.context.freshness === "stale") {
    return { mark: "stale", word: "판단 가능 (이전 결과)", cls: "is-stale", stroke: "var(--stale-mark)" };
  }
  return base;
}

function verdictTag(card, size) {
  var v = verdictOf(card);
  var tag = h("span", { class: "row gap-6 " + (size === 15 ? "tag-15" : "tag-13") + " " + v.cls });
  tag.appendChild(icon(v.mark, 15, v.stroke));
  tag.appendChild(h("span", { text: v.word }));
  return tag;
}

function freshnessTag(context) {
  if (!context) return null;
  var map = {
    current: ["ready", "var(--ok-mark)", "기록된 입력 기준 · 차이 없음", "is-unknown"],
    stale: ["stale", "var(--stale-mark)", "기록된 입력 이후 변경 있음", "is-stale"],
    unknown: ["unknown", "var(--stale-mark)", "현재 적용 여부 미확인", "is-unknown"]
  };
  var it = map[context.freshness] || map.unknown;
  var tag = h("span", { class: "row gap-6 caption " + it[3] });
  tag.appendChild(icon(it[0], 13, it[1]));
  tag.appendChild(h("span", { text: it[2] }));
  return tag;
}

function dot() { return h("span", { "aria-hidden": "true", class: "bullet", text: "·" }); }

function countsLine(counts) {
  if (!counts || !counts.all) return h("span", { class: "body-sm", text: "조건 정보 없음" });
  var all = counts.all;
  var line = h("span", { class: "row gap-10 wrap-row body-sm" });
  line.appendChild(h("span", { text: "조건 " + all.total + "개" }));
  line.appendChild(dot());
  [["확인됨", all.verified, "is-ready"], ["실패", all.failed, null],
   ["판단불가", all.inconclusive, null], ["미확인", all.unobserved, null]].forEach(function (pair) {
    var cell = h("span", { class: pair[2] && pair[1] ? pair[2] : "" });
    cell.appendChild(h("span", { class: "caption", text: pair[0] + " " }));
    cell.appendChild(h("strong", { class: "strong", text: String(pair[1]) }));
    line.appendChild(cell);
  });
  return line;
}

/* ---------- transport ---------- */

async function call(path, options) {
  var settings = options || {};
  var headers = {};
  var payload = null;
  if (settings.body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(settings.body);
  }
  var method = settings.method || "GET";
  if (method !== "GET" && csrf) headers["X-OwnHands-CSRF"] = csrf;
  var response;
  try {
    response = await fetch(API + path, {
      method: method, headers: headers, body: payload,
      credentials: "same-origin", cache: "no-store", redirect: "error"
    });
  } catch (error) {
    return { status: 0, data: null };
  }
  var text = await response.text();
  var data = null;
  if (text) { try { data = JSON.parse(text); } catch (error) { data = null; } }
  return { status: response.status, data: data };
}

var ERRORS = {
  INVALID_QUERY: "요청이 이 화면에 맞지 않습니다.",
  ORIGIN_DENIED: "이 주소에서는 열 수 없습니다. 서버가 안내한 loopback 주소로 접속해 주세요.",
  CSRF_FAILED: "세션 확인이 필요합니다.",
  NOT_FOUND: "찾는 자료가 없습니다.",
  LIST_CHANGED: "읽는 동안 목록이 바뀌었습니다. 처음부터 다시 불러옵니다.",
  SOURCE_CHANGED: "읽는 동안 원본이 바뀌었습니다. 다시 불러옵니다.",
  RECIPE_CHANGED: "설명 생성 기준이 바뀌었습니다. 목록을 다시 불러옵니다.",
  SOURCE_UNAVAILABLE: "검토 기록을 읽을 수 없습니다.",
  UNSUPPORTED_SCHEMA: "이 원본 형식은 지원하지 않습니다.",
  SOURCE_INTEGRITY_ERROR: "원본을 검증할 수 없습니다."
};

function errorText(result) {
  if (result.status === 0) return "서버에 연결하지 못했습니다.";
  var code = result.data && result.data.error && result.data.error.code;
  return ERRORS[code] || "요청을 처리하지 못했습니다.";
}

/* ---------- shell ---------- */

function view() { return document.getElementById("view"); }
function announce(message) { document.getElementById("live").textContent = message || ""; }

function paint(node) {
  var main = view();
  main.textContent = "";
  main.appendChild(node);
}

function crumbs(items) {
  var bar = document.getElementById("crumb");
  bar.textContent = "";
  items.forEach(function (item, index) {
    if (index) bar.appendChild(dot());
    if (item.hash) {
      bar.appendChild(h("a", { class: "caption", href: "#" + item.hash, text: item.label }));
    } else {
      bar.appendChild(h("span", { class: "caption", text: item.label }));
    }
  });
}

function notice(kind, message, action) {
  var box = h("div", { class: "card tinted-strong card-sm row gap-10 wrap-row", role: "status" });
  box.appendChild(icon(kind, 16, kind === "blocked" ? "var(--danger-mark)" : "var(--stale-mark)"));
  box.appendChild(h("span", { class: "body-sm grow", text: message }));
  if (action) box.appendChild(action);
  return box;
}

/* ---------- session ---------- */

function loginScreen(message) {
  var target = location.hash || "#/";
  var field = h("input", {
    class: "input mono", id: "token", type: "password", autocomplete: "off",
    placeholder: "터미널에 표시된 토큰 붙여넣기", required: true
  });
  var problem = h("p", { class: "body-sm is-blocked", role: "alert", text: message || "" });
  var form = h("form", {
    class: "card card-lg stack gap-16 form-width",
    onsubmit: async function (event) {
      event.preventDefault();
      var value = field.value;
      field.value = "";                       /* cleared the moment it is read */
      var result = await call("/session", { method: "POST", body: { token: value } });
      if (result.status === 200 && result.data && result.data.csrf_token) {
        csrf = result.data.csrf_token;
        announce("접속했습니다.");
        render();
        return;
      }
      problem.textContent = result.status === 401
        ? "이 토큰으로는 접속할 수 없습니다. 자동으로 다시 시도하지 않습니다."
        : errorText(result);
      field.focus();
    }
  });
  form.appendChild(h("div", { class: "stack gap-8" },
    h("h1", { class: "page-title", class: "t-24", text: "접속 토큰을 입력하세요" }),
    h("p", { class: "body-sm", text: "서버를 시작할 때 터미널에 한 번 표시된 토큰입니다." })));
  form.appendChild(problem);
  if (target !== "#/") {
    form.appendChild(h("div", { class: "card tinted card-sm row gap-8" },
      icon("back", 14, "var(--ink-muted)"),
      h("span", { class: "caption", text: "접속 후 보던 화면으로 돌아갑니다 · " + target })));
  }
  form.appendChild(h("div", { class: "stack gap-6" },
    h("label", { class: "caption", for: "token", text: "접속 토큰" }), field));
  form.appendChild(h("button", { class: "primary-button", type: "submit", text: "접속" }));
  form.appendChild(h("span", { class: "caption",
    text: "토큰은 입력한 뒤 즉시 지워지며 주소·브라우저 저장소·콘솔에 남지 않습니다. "
        + "모델 credential은 서버에만 있고 이 화면으로 받지 않습니다." }));
  crumbs([]);
  paint(h("div", { class: "wrap row center" }, form));
  window.setTimeout(function () { field.focus(); }, 0);
}

/* ---------- presentation rendering ---------- */

/* Each TextFact keeps its own kind label, so 변경 의도 · 관찰된 결과 · 미확인이
 * 한 문단에서 섞이지 않는다. The labels are the reader's questions, not the
 * verifier's vocabulary. */
var KIND = {
  intent: ["왜 바꿨나", "is-unknown"],
  observed: ["근거 있는 것", "is-ready"],
  gap: ["아직 근거 없는 것", "is-needs"],
  inference: ["추정", "is-stale"]
};

function factRow(label, cls, value) {
  return h("div", { class: "facts" },
    h("span", { class: "caption strong " + cls, text: label }), value);
}

function factRows(presentation, options) {
  var settings = options || {};
  var rows = [];
  var summary = presentation.summary || [];
  if (presentation.fallback) {
    /* These lines are the server's deterministic sentences, not generated
     * facts, so they must not wear the kind labels. */
    summary.forEach(function (fact) {
      rows.push(h("p", { class: settings.size === 14 ? "t-14" : "t-15", text: fact.text }));
    });
    return rows;
  }
  function pick(kind) { return summary.filter(function (f) { return f && f.kind === kind; }); }
  if (!settings.skipIntent) {
    pick("intent").forEach(function (fact) {
      rows.push(factRow(KIND.intent[0], KIND.intent[1],
        h("span", { class: settings.size === 14 ? "t-14" : "t-15", text: fact.text })));
    });
  }
  var changes = presentation.key_changes || [];
  if (changes.length) {
    var list = h("ul", { class: "stack gap-6" });
    changes.forEach(function (fact) {
      var item = h("li", { class: "row gap-8 top" });
      item.appendChild(h("span", { "aria-hidden": "true", class: "is-unknown", text: "•" }));
      item.appendChild(h("span", { text: fact.text }));
      list.appendChild(item);
    });
    rows.push(factRow("한 일", "is-unknown", list));
  }
  ["observed", "gap", "inference"].forEach(function (kind) {
    pick(kind).forEach(function (fact) {
      rows.push(factRow(KIND[kind][0], KIND[kind][1],
        h("span", { class: settings.size === 14 ? "t-14" : "t-15", text: fact.text })));
    });
  });
  return rows;
}

function presentationNote(presentation) {
  if (!presentation || presentation.status === "ready") return null;
  var word = {
    pending: ["stale", "쉬운 설명을 준비하고 있습니다. 검증 결과와 근거는 지금 바로 확인할 수 있습니다."],
    failed: ["needs", "쉬운 설명을 생성하지 못했습니다. 검증 결과와 근거는 계속 확인할 수 있습니다."],
    unavailable: ["unknown", presentation.reason_code === "source_partial"
      ? "근거 일부를 읽을 수 없어, 원본을 확인하기 전까지 쉬운 설명을 표시하지 않습니다."
      : "쉬운 설명 생성이 설정되어 있지 않습니다. 저장된 결과와 근거는 그대로 볼 수 있습니다."],
    absent: ["unknown", "아직 쉬운 설명이 없습니다."]
  }[presentation.status];
  if (!word) return null;
  var row = h("div", { class: "row gap-8 top" });
  row.appendChild(icon(word[0], 14, "var(--ink-muted)"));
  row.appendChild(h("span", { class: "caption", text: word[1] }));
  return row;
}

/* ---------- generation contract ---------- */

/* A search is browsing, not a first real view: it must never be the reason a
 * summary is generated. The server's own search is cached-only for the same
 * reason (`summary_search: cached_only`). */
function searching() {
  return !!(parseHash().query.q || "").trim();
}

function canEnsure(key) {
  if (!csrf) return false;                       /* refreshed: CSRF is gone */
  if (searching()) return false;
  if (inflight.has(key) || asked.has(key)) return false;
  var until = cooldown.get(key);
  return !(until && Date.now() < until);
}

/* The server allows two attempts; the second is spent at the next real view once
 * the cooldown has passed. So `failed` is ensurable again, `ready` never is. */
function ensurable(presentation) {
  if (!presentation) return false;
  if (presentation.status === "absent") return true;
  return presentation.status === "failed"
    && (!presentation.retry_after || Date.parse(presentation.retry_after) <= Date.now());
}

async function ensure(key, intent, recipeHash, onDone) {
  if (!canEnsure(key)) return;
  inflight.add(key);
  asked.add(key);
  var body = { view_intent: intent };
  if (recipeHash) body.recipe_hash = recipeHash;
  var result = await call("/snapshots/" + encodeURIComponent(key) + "/presentation/ensure",
                          { method: "POST", body: body });
  inflight.delete(key);
  if (result.status === 202) { poll(key, onDone); return; }
  if (result.status !== 200) {
    asked.delete(key);          /* the server settled nothing: a later view may ask again */
    return;
  }
  if (result.data) {
    if (result.data.status === "failed" && result.data.retry_after) {
      cooldown.set(key, Date.parse(result.data.retry_after));
    }
    onDone(result.data);
  }
  /* 403/409/503 stop here: no replay, no timer. */
}

/* `remember` is the hidden-tab case: the poll is paused, not abandoned, so the
 * key and its continuation are kept for resumePolls. Navigation forgets them. */
function stopPolls(remember) {
  polls.forEach(function (state, key) {
    window.clearTimeout(state.timer);
    if (remember) suspended.set(key, { onDone: state.onDone, step: state.step, spent: state.spent });
  });
  polls.clear();
  if (!remember) suspended.clear();
}

async function refresh(key) {
  var token = routeToken;
  var result = await call("/snapshots/" + encodeURIComponent(key) + "/presentation");
  if (token !== routeToken) return null;
  return result.status === 200 ? result.data : null;
}

/* SDD §7.2.6 — 1s, 2s, then 5s, giving up at 60s, paused while the tab is hidden. */
var WAITS = [1000, 2000, 5000];

function poll(key, onDone, step, spent) {
  var at = step || 0;
  var used = spent || 0;
  function tick() {
    if (document.hidden) {
      suspended.set(key, { onDone: onDone, step: at, spent: used });
      polls.delete(key);
      return;
    }
    var wait = WAITS[Math.min(at, WAITS.length - 1)];
    at += 1;
    used += wait;
    if (used > 60000) {
      polls.delete(key);
      announce("설명 생성이 오래 걸립니다. 화면을 다시 열면 이어서 확인합니다.");
      return;
    }
    var timer = window.setTimeout(async function () {
      polls.delete(key);
      var data = await refresh(key);
      if (data === null) return;                  /* navigated away: drop it */
      if (data.status === "pending") { tick(); return; }
      if (data.status === "failed" && data.retry_after) {
        cooldown.set(key, Date.parse(data.retry_after));
      }
      onDone(data);
    }, wait);
    polls.set(key, { timer: timer, onDone: onDone, step: at, spent: used });
  }
  tick();
}

/* Coming back resumes each paused poll from a GET and leaves the rendered page
 * (and its scroll position) alone. */
async function resumePolls() {
  var pending = Array.from(suspended.entries());
  suspended.clear();
  for (var i = 0; i < pending.length; i += 1) {
    var key = pending[i][0];
    var state = pending[i][1];
    var data = await refresh(key);
    if (data === null) continue;
    if (data.status === "pending") { poll(key, state.onDone, state.step, state.spent); continue; }
    if (data.status === "failed" && data.retry_after) {
      cooldown.set(key, Date.parse(data.retry_after));
    }
    state.onDone(data);
  }
}

document.addEventListener("visibilitychange", function () {
  if (document.hidden) { stopPolls(true); return; }
  resumePolls();
});

function sessionNotice() {
  return notice("unknown",
    "새로고침으로 세션 확인 값이 사라져 쉬운 설명을 새로 만들지 않습니다. 저장된 결과와 근거는 그대로 볼 수 있습니다.",
    h("button", { class: "chip", text: "세션 확인",
      onclick: function () { loginScreen(null); } }));
}

/* ---------- Review List ---------- */

/* A v1 Review records no checks. Its Claim still carries its own Observations,
 * so read those instead of inventing a check that was never recorded. */
function claimObservations(claim) {
  return claim.observations || [];
}

function evidenceKeysOf(claim) {
  var keys = [];
  claimObservations(claim).forEach(function (observation) {
    (observation.evidence_links || []).forEach(function (link) {
      if (keys.indexOf(link.evidence_key) === -1) keys.push(link.evidence_key);
    });
  });
  return keys;
}

/* The newest stored Snapshot is not always the activated one. */
function activeElsewhere(card) {
  var active = card.context && card.context.active_snapshot_key;
  if (!active || active === card.snapshot_key) return null;
  return h("a", { class: "caption is-stale",
    href: "#/snapshots/" + encodeURIComponent(active),
    text: "현재 적용 중인 보고서는 따로 있습니다" });
}

function issueRef(card) {
  var ref = card.issue && card.issue.ref;
  return ref && ref.id ? String(ref.id) : "";
}

function reviewCard(card, observer) {
  var box = h("article", { class: "card review-card" });
  var head = h("div", { class: "row gap-10 top" });
  if (card.presentation && card.presentation.icon) {
    head.appendChild(h("span", { "aria-hidden": "true", class: "emoji-sm", text: card.presentation.icon }));
  }
  head.appendChild(h("span", { class: "caption mono nudge", text: issueRef(card) }));
  head.appendChild(h("a", { class: "card-title grow inherit", href: "#/snapshots/" + encodeURIComponent(card.snapshot_key),
    text: (card.issue && card.issue.title) || "제목 없음" }));
  head.appendChild(verdictTag(card));
  box.appendChild(head);

  var line = h("div", { class: "row gap-16 wrap-row base" });
  var summary = card.presentation && card.presentation.summary && card.presentation.summary[0];
  line.appendChild(h("p", { class: "body-sm grow-320",
    text: summary ? summary.text : ((card.presentation && card.presentation.headline
      && card.presentation.headline.text) || "") }));
  var meta = h("div", { class: "row gap-10 wrap-row" });
  meta.appendChild(countsLine(card.counts));
  meta.appendChild(dot());
  var fresh = freshnessTag(card.context);
  if (fresh) meta.appendChild(fresh);
  if (card.context && card.context.newer_snapshot_key) {
    meta.appendChild(h("span", { class: "caption is-stale", text: "더 최근 보고서 있음" }));
  }
  var active = activeElsewhere(card);
  if (active) meta.appendChild(active);
  meta.appendChild(h("span", { class: "caption", text: "Snapshot " + stamp(card.snapshot_created_at) }));
  line.appendChild(meta);
  box.appendChild(line);

  /* 실제 viewport에 들어온 카드만 ensure한다. */
  if (observer && ensurable(card.presentation)) {
    box.setAttribute("data-key", card.snapshot_key);
    box.setAttribute("data-recipe", card.presentation.recipe_hash || "");
    observer.observe(box);
  }
  return box;
}

function pinnedCard(card, observer) {
  var box = h("section", { class: "card card-lg" });
  var grid = h("div", { class: "split" });
  var left = h("div", { class: "stack gap-12 grow" });
  left.appendChild(h("div", { class: "row gap-8 id-row" },
    h("span", { class: "caption mono", text: issueRef(card) }),
    h("h3", { class: "card-title grow", text: (card.issue && card.issue.title) || "제목 없음" })));
  var presentation = card.presentation || {};
  var headline = presentation.headline && presentation.headline.text;
  if (headline) {
    left.appendChild(h("div", { class: "row gap-8 top" },
      presentation.icon ? h("span", { "aria-hidden": "true", class: "emoji-md", text: presentation.icon }) : null,
      h("p", { class: "grow headline", text: headline })));
  }
  left.appendChild(h("div", { class: "stack gap-8" }, factRows(presentation, { skipIntent: true, size: 14 })));
  var note = presentationNote(presentation);
  if (note) left.appendChild(note);
  left.appendChild(h("a", { class: "link-row", href: "#/snapshots/" + encodeURIComponent(card.snapshot_key) },
    h("span", { text: "전체 검증 결과와 근거 보기" }), icon("chev", 14)));

  var right = h("div", { class: "stack gap-12 rail grow" });
  right.appendChild(verdictTag(card, 15));
  right.appendChild(h("p", { class: "body-sm", text: card.state_reason || "" }));
  var facts = h("div", { class: "stack gap-6" });
  facts.appendChild(countsLine(card.counts));
  var fresh = freshnessTag(card.context);
  if (fresh) facts.appendChild(fresh);
  var activeCard = activeElsewhere(card);
  if (activeCard) facts.appendChild(activeCard);
  facts.appendChild(h("span", { class: "caption", text: "Snapshot " + stamp(card.snapshot_created_at) }));
  right.appendChild(facts);
  grid.appendChild(left);
  grid.appendChild(right);
  box.appendChild(grid);
  if (observer && ensurable(presentation)) {
    box.setAttribute("data-key", card.snapshot_key);
    box.setAttribute("data-recipe", presentation.recipe_hash || "");
    observer.observe(box);
  }
  return box;
}

function viewportObserver() {
  if (typeof IntersectionObserver !== "function") return null;
  return new IntersectionObserver(function (entries, self) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var node = entry.target;
      self.unobserve(node);
      ensure(node.getAttribute("data-key"), "list_visible", node.getAttribute("data-recipe"),
        function () { render(); });
    });
  }, { rootMargin: "0px" });
}

function listQuery(query, cursor) {
  var parts = [];
  if (query.filter && query.filter !== "all") parts.push("filter=" + encodeURIComponent(query.filter));
  if (query.q) parts.push("q=" + encodeURIComponent(query.q));
  if (cursor) parts.push("cursor=" + encodeURIComponent(cursor));
  return parts.length ? "?" + parts.join("&") : "";
}

function goList(query) {
  location.hash = "#/" + listQuery(query, null);
}

function searchBox(query) {
  var field = h("input", { class: "input", type: "search", id: "q", name: "q",
    value: query.q || "", placeholder: "제목 또는 저장된 요약 검색", maxlength: "200" });
  var form = h("form", { class: "stack gap-6 search", role: "search",
    onsubmit: function (event) {
      event.preventDefault();
      goList({ filter: query.filter, q: field.value.trim() });
    } });
  form.appendChild(h("label", { class: "caption", for: "q", text: "검색" }));
  form.appendChild(h("div", { class: "row gap-8 wrap-row" }, icon("search", 15, "var(--ink-muted)"), field,
    h("button", { class: "chip", type: "submit", text: "검색" }),
    query.q ? h("button", { class: "chip", type: "button", text: "지우기",
      onclick: function () { goList({ filter: query.filter, q: "" }); } }) : null));
  form.appendChild(h("span", { class: "caption",
    text: "검색 범위는 작업 제목과 이미 생성된 요약입니다. 검색이 새 요약을 만들지 않습니다." }));
  return form;
}

async function listScreen(query) {
  var token = routeToken;
  var result = await call("/reviews" + listQuery(query, null));
  if (token !== routeToken) return;
  if (result.status === 401) { loginScreen(null); return; }
  crumbs([{ label: "검토 결과" }]);
  var page = h("div", { class: "wrap stack gap-16" });
  if (result.status !== 200 || !result.data) {
    page.appendChild(h("h1", { class: "page-title", text: "검토 결과" }));
    page.appendChild(notice("blocked", errorText(result),
      h("button", { class: "chip", text: "다시 시도", onclick: function () { render(); } })));
    paint(page);
    return;
  }
  var cards = result.data.items || [];
  var searched = !!(query.q || "").trim();

  var subtitle = h("span", { class: "body-sm" });
  var countLine = function (total) {
    subtitle.textContent = !total ? ""
      : (searched ? "검색 결과 " + total + "건"
         : "서로 다른 작업 " + total + "건 · 작업마다 검토 하나");
  };
  countLine(cards.length);
  page.appendChild(h("div", { class: "stack gap-6" },
    h("h1", { class: "page-title", text: "검토 결과" }), subtitle));
  page.appendChild(searchBox(query));

  var chips = h("div", { class: "row gap-8 wrap-row" });
  [["all", "전체"], ["needs-review", "확인 필요"], ["blocked", "차단"],
   ["stale", "이전 결과"], ["ready", "판단 가능"]].forEach(function (pair) {
    chips.appendChild(h("button", {
      class: "chip", "aria-pressed": (query.filter || "all") === pair[0] ? "true" : "false",
      text: pair[1],
      onclick: function () { goList({ filter: pair[0], q: query.q }); }
    }));
  });
  page.appendChild(chips);
  if (!csrf && !searched) page.appendChild(sessionNotice());

  if (!cards.length) {
    page.appendChild(h("div", { class: "card pad-empty" },
      h("p", { text: searched ? "‘" + query.q + "’와 일치하는 결과가 없습니다."
        : (query.filter && query.filter !== "all" ? "이 조건에 해당하는 검토가 없습니다."
           : "저장된 검토 결과가 없습니다.") }),
      h("p", { class: "body-sm", text: searched
        ? "검색은 제목과 이미 생성된 요약만 대상으로 합니다."
        : "검토가 저장되면 여기에 나타납니다." })));
    paint(page);
    return;
  }

  var observer = viewportObserver();
  page.appendChild(h("section", { class: "stack gap-8" },
    h("h2", { class: "card-title", text: searched ? "가장 먼저 볼 결과" : "먼저 볼 것" }),
    h("p", { class: "body-sm", text: "서로 다른 작업 가운데 가장 확인이 필요한 작업 1건입니다. "
      + "순서는 서버가 정합니다 — 확인 필요 → 검증 차단 → 이전 결과 → 판단 가능. 최근 순이 아닙니다." }),
    pinnedCard(cards[0], observer)));

  var rest = h("ul", { class: "stack gap-10" });
  cards.slice(1).forEach(function (card) { rest.appendChild(h("li", {}, reviewCard(card, observer))); });
  var restLabel = h("h2", { class: "card-title t-15 is-unknown",
    text: "다른 작업의 검토 " + Math.max(0, cards.length - 1) + "건" });
  var restSection = h("section", { class: "stack gap-8" }, restLabel, rest);
  page.appendChild(restSection);

  /* next_cursor paging: a page is appended, never spliced into a different list. */
  var cursor = result.data.next_cursor;
  var listToken = result.data.list_token;
  var shown = cards.length;
  if (cursor) {
    var more = h("button", { class: "chip", text: "더 보기" });
    var moreRow = h("div", { class: "row gap-8 wrap-row" }, more,
      h("span", { class: "caption", text: "서버가 준 cursor로만 이어 읽습니다." }));
    more.addEventListener("click", async function () {
      more.disabled = true;
      var next = await call("/reviews" + listQuery(query, cursor));
      more.disabled = false;
      var changed = next.status === 200 && next.data && next.data.list_token !== listToken;
      if (next.status !== 200 || !next.data || changed) {
        var code = changed ? "LIST_CHANGED"
          : (next.data && next.data.error && next.data.error.code);
        moreRow.remove();
        restSection.appendChild(notice(code === "LIST_CHANGED" ? "stale" : "blocked",
          code === "LIST_CHANGED"
            ? "목록이 그사이 바뀌었습니다. 서로 다른 목록의 페이지를 이어 붙이지 않고 처음부터 다시 읽습니다."
            : errorText(next),
          h("button", { class: "chip", text: "처음부터 다시 불러오기",
            onclick: function () { render(); } })));
        return;
      }
      (next.data.items || []).forEach(function (card) {
        rest.appendChild(h("li", {}, reviewCard(card, observer)));
        shown += 1;
      });
      restLabel.textContent = "다른 작업의 검토 " + Math.max(0, shown - 1) + "건";
      countLine(shown);
      cursor = next.data.next_cursor;
      if (!cursor) moreRow.remove();
    });
    restSection.appendChild(moreRow);
  }
  paint(page);
  if (!observer) {
    cards.forEach(function (card) {
      if (ensurable(card.presentation)) {
        ensure(card.snapshot_key, "list_visible", card.presentation.recipe_hash,
          function () { render(); });
      }
    });
  }
}

/* ---------- Review Detail ---------- */

var STATE_WORD = { verified: "확인됨", failed: "실패", inconclusive: "판단불가", unobserved: "미확인" };
var CLAIM_MARK = {
  verified: ["ready", "var(--ok-mark)", "is-ready"],
  failed: ["blocked", "var(--danger-mark)", "is-blocked"],
  inconclusive: ["needs", "var(--warn-mark)", "is-needs"],
  unobserved: ["unknown", "var(--stale-mark)", "is-unknown"]
};

function claimTag(status, size) {
  var it = CLAIM_MARK[status] || CLAIM_MARK.unobserved;
  var tag = h("span", { class: "row gap-6 caption strong " + it[2] });
  tag.appendChild(icon(it[0], 14, it[1]));
  tag.appendChild(h("span", { text: STATE_WORD[status] || status }));
  return tag;
}

function banners(detail) {
  var out = [];
  var context = detail.context || {};
  if (context.read_health && context.read_health !== "complete") {
    out.push(notice("unknown", "자료 확인 필요 — 근거 일부를 읽을 수 없습니다. "
      + "아래 판정과 숫자는 저장 당시 그대로이고, 읽을 수 없는 근거만 따로 표시합니다."));
  }
  if (context.freshness === "stale") {
    out.push(notice("stale", "기록된 입력 이후에 변경이 있습니다. 아래 판정과 숫자는 이 Snapshot 기준이며 그대로 보존됩니다.",
      context.newer_snapshot_key
        ? h("a", { class: "caption", href: "#/snapshots/" + encodeURIComponent(context.newer_snapshot_key),
            text: "더 최근 보고서 열기" })
        : null));
  }
  if (context.new_evidence_available) {
    out.push(notice("doc", "이 보고서 이후 새 근거가 등록됐습니다. 아래 결과에는 반영되어 있지 않습니다."));
  }
  (detail.context_notices || []).forEach(function (line) {
    out.push(notice("unknown", line));
  });
  return out;
}

function verificationSummary(detail) {
  var counts = detail.counts;
  var box = h("section", { class: "card card-pad stack gap-12" });
  box.appendChild(h("h2", { class: "card-title", text: "검증 요약" }));
  if (!counts || !counts.all) {
    box.appendChild(h("p", { class: "body-sm", text: "이 형식의 Review에는 집계가 기록되지 않았습니다." }));
    return box;
  }
  var grid = h("div", { class: "counts" });
  [["확인됨", counts.all.verified, "is-ready"], ["실패", counts.all.failed, ""],
   ["판단불가", counts.all.inconclusive, ""], ["미확인", counts.all.unobserved, ""]].forEach(function (cell) {
    grid.appendChild(h("div", { class: "stack gap-2" },
      h("span", { class: "caption", text: cell[0] }),
      h("span", { class: "count-big " + cell[2], text: String(cell[1]) })));
  });
  box.appendChild(grid);
  box.appendChild(h("span", { class: "caption", text: "전체 " + counts.all.total
    + " · 필수 " + counts.required.total + " · 선택 " + counts.optional.total
    + " (선택 제외 " + counts.excluded_optional_count + ") · 저장된 Review 판정을 그대로 표시합니다" }));
  return box;
}

function attentionCard(detail) {
  var problems = detail.problems || [];
  if (!problems.length) return null;
  var box = h("section", { class: "stack gap-10" });
  box.appendChild(h("div", { class: "row gap-8 wrap-row" },
    h("h2", { class: "card-title", text: "주의 필요" }),
    h("span", { class: "badge", text: problems.length + "건" })));
  var list = h("ul", { class: "stack gap-8" });
  problems.forEach(function (problem, index) {
    var item = h("li", { class: "card tinted-strong card-sm stack gap-6" });
    item.appendChild(h("div", { class: "row gap-8 top" },
      icon(CLAIM_MARK[problem.kind === "failure" ? "failed" : "inconclusive"][0], 15,
        problem.kind === "failure" ? "var(--danger-mark)" : "var(--warn-mark)"),
      h("span", { class: "grow t-14-strong",
        text: problem.description || problem.reason_code }),
      h("span", { class: "badge", text: (problem.required ? "필수" : "선택") + " · " + problem.kind })));
    if (problem.claim_id) {
      item.appendChild(h("a", { class: "caption indent",
        href: "#/snapshots/" + encodeURIComponent(detail.snapshot_key)
          + "/claims/" + encodeURIComponent(problem.claim_id),
        text: "이 조건 열기" }));
    }
    if (index >= 3) item.hidden = true;
    list.appendChild(item);
  });
  box.appendChild(list);
  var rest = problems.length - 3;
  if (rest > 0) {
    var open = false;
    var toggle = h("button", { class: "chip", "aria-expanded": "false",
      text: "추가 " + rest + "건 보기" });
    toggle.addEventListener("click", function () {
      open = !open;
      Array.prototype.slice.call(list.children, 3).forEach(function (node) { node.hidden = !open; });
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.textContent = open ? "추가 " + rest + "건 접기" : "추가 " + rest + "건 보기";
      announce(open ? "주의 " + problems.length + "건을 모두 표시했습니다." : "주의 3건만 표시합니다.");
    });
    box.appendChild(toggle);
  }
  return box;
}

function nextCheckCard(presentation) {
  var items = (presentation && presentation.next_checks) || [];
  if (!items.length) return null;
  var list = h("ul", { class: "stack gap-6" });
  items.forEach(function (fact) {
    list.appendChild(h("li", { class: "row gap-8 top" },
      h("span", { "aria-hidden": "true", class: "is-unknown", text: "•" }),
      h("span", { class: "body-sm", text: fact.text })));
  });
  return h("section", { class: "card tinted card-sm stack gap-8" },
    h("h2", { class: "card-title t-15-strong", text: "다음으로 확인할 것" }), list);
}

function evidenceList(detail) {
  var claims = detail.claims || [];
  var box = h("section", { class: "stack gap-10" });
  box.appendChild(h("div", { class: "row gap-8" },
    h("h2", { class: "card-title", text: "근거 탐색" }),
    h("span", { class: "badge", text: "조건 " + claims.length + "개 전부" })));
  var legacy = detail.source_contract_version === 1;
  box.appendChild(h("p", { class: "body-sm", text: legacy
    ? "이 Review는 이전 형식이라 상세 검사 항목이 기록되지 않았습니다. 저장된 Observation과 근거는 그대로 볼 수 있습니다."
    : "조건을 열면 저장된 Before/After와 근거 목록을 볼 수 있습니다." }));
  var list = h("ul", { class: "stack gap-6" });
  claims.forEach(function (claim) {
    var checks = claim.checks || [];
    var evidence = checks.length
      ? checks.reduce(function (sum, check) { return sum + (check.evidence_count || 0); }, 0)
      : evidenceKeysOf(claim).length;
    var row = h("a", { class: "list-row inherit",
      href: "#/snapshots/" + encodeURIComponent(detail.snapshot_key)
        + "/claims/" + encodeURIComponent(claim.id) });
    row.appendChild(icon(CLAIM_MARK[claim.status][0], 15, CLAIM_MARK[claim.status][1]));
    row.appendChild(h("span", { class: "grow t-14", text: claim.text }));
    row.appendChild(h("span", { class: "caption", text: (claim.required ? "필수" : "선택")
      + (legacy ? "" : " · 검사 " + checks.length) + " · 근거 " + evidence }));
    row.appendChild(claimTag(claim.status));
    row.appendChild(icon("chev", 14, "var(--ink-muted)"));
    list.appendChild(h("li", {}, row));
  });
  box.appendChild(list);
  return box;
}

async function detailScreen(key, claimId) {
  var token = routeToken;
  var result = await call("/snapshots/" + encodeURIComponent(key));
  if (token !== routeToken) return;
  if (result.status === 401) { loginScreen(null); return; }
  if (result.status !== 200 || !result.data) {
    crumbs([{ label: "검토 결과", hash: "/" }, { label: "열 수 없음" }]);
    paint(h("div", { class: "wrap stack gap-16" },
      h("a", { class: "link-row", href: "#/" }, icon("back", 13), h("span", { text: "검토 목록" })),
      notice("blocked", errorText(result))));
    return;
  }
  var detail = result.data;
  var presentation = detail.presentation || {};
  crumbs([{ label: "검토 결과", hash: "/" },
          { label: (detail.issue && detail.issue.title) || detail.snapshot_key.slice(0, 12) }]);

  var page = h("div", { class: "wrap stack gap-16" });
  page.appendChild(h("a", { class: "link-row", href: "#/" },
    icon("back", 13), h("span", { text: "검토 목록" })));
  page.appendChild(h("div", { class: "stack gap-6" },
    h("div", { class: "row gap-10 base id-row" },
      h("span", { class: "caption mono", text: issueRef(detail) }),
      h("h1", { class: "page-title grow", text: (detail.issue && detail.issue.title) || "제목 없음" })),
    h("span", { class: "caption", text: "Snapshot " + stamp(detail.snapshot_created_at)
      + " · 이 화면의 모든 값은 이 Snapshot 하나에서 나옵니다" })));
  banners(detail).forEach(function (box) { page.appendChild(box); });
  if (!csrf && ensurable(presentation)) page.appendChild(sessionNotice());

  var summary = h("section", { class: "card card-lg stack gap-16" });
  var headline = presentation.headline && presentation.headline.text;
  summary.appendChild(h("div", { class: "row gap-10 top" },
    presentation.icon ? h("span", { "aria-hidden": "true", class: "emoji-lg", text: presentation.icon }) : null,
    h("h2", { class: "section-title grow", text: headline || (detail.issue && detail.issue.title) || "" })));
  summary.appendChild(h("div", { class: "stack gap-10" }, factRows(presentation)));
  var note = presentationNote(presentation);
  if (note) summary.appendChild(note);

  var status = h("section", { class: "card tinted-strong card-pad stack gap-10" });
  status.appendChild(h("span", { class: "caption", text: "저장된 Review 판정" }));
  var verdict = verdictOf(detail);
  status.appendChild(h("div", { class: "row gap-8" }, icon(verdict.mark, 22, verdict.stroke),
    h("span", { class: "verdict-big " + verdict.cls, text: verdict.word })));
  status.appendChild(h("p", { text: detail.state_reason || "" }));
  status.appendChild(h("hr", { class: "sep" }));
  var fresh = freshnessTag(detail.context);
  if (fresh) status.appendChild(fresh);
  if (detail.context && detail.context.checked_at) {
    status.appendChild(h("span", { class: "caption", text: stamp(detail.context.checked_at) + " 확인" }));
  }

  var split = h("div", { class: "detail-split" });
  var main = h("div", { class: "stack gap-16 grow" });
  main.appendChild(summary);
  main.appendChild(verificationSummary(detail));
  main.appendChild(evidenceList(detail));
  var rail = h("div", { class: "stack gap-16 grow side" });
  rail.appendChild(status);
  var attention = attentionCard(detail);
  if (attention) rail.appendChild(attention);
  var next = nextCheckCard(presentation);
  if (next) rail.appendChild(next);
  split.appendChild(main);
  split.appendChild(rail);
  page.appendChild(split);
  paint(page);

  if (restoreClaim) {
    var target = document.querySelector('a[href$="/claims/' + restoreClaim + '"]');
    if (target) target.focus();
    else view().focus();
    restoreClaim = null;
  }
  if (ensurable(presentation)) {
    ensure(key, "detail", presentation.recipe_hash, function () { render(); });
  }
  if (claimId) openDrawer(detail, claimId);
}

/* ---------- Evidence Drawer ---------- */

var drawerReturn = null;

function closeDrawer(goBack) {
  var overlay = document.getElementById("overlay");
  overlay.textContent = "";
  document.removeEventListener("keydown", drawerKeys, true);
  if (goBack && location.hash.indexOf("/claims/") !== -1) {
    restoreClaim = location.hash.split("/claims/")[1];
    location.hash = location.hash.split("/claims/")[0];
    return;                                   /* focus is restored after the re-render */
  }
  if (drawerReturn && document.contains(drawerReturn)) drawerReturn.focus();
  drawerReturn = null;
}

function drawerKeys(event) {
  if (event.key === "Escape") { event.preventDefault(); closeDrawer(true); return; }
  if (event.key !== "Tab") return;
  var panel = document.querySelector(".drawer");
  if (!panel) return;
  var focusable = panel.querySelectorAll("a[href], button, input, [tabindex]:not([tabindex='-1'])");
  if (!focusable.length) return;
  var first = focusable[0];
  var last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function evidenceLinks(detail, observations) {
  var list = h("ul", { class: "stack gap-6" });
  observations.forEach(function (observation) {
    (observation.evidence_links || []).forEach(function (link) {
      list.appendChild(h("li", {}, h("a", { class: "link-row",
        href: "#/snapshots/" + encodeURIComponent(detail.snapshot_key)
          + "/evidence/" + encodeURIComponent(link.evidence_key) },
        h("span", { text: "상세 근거 열기" }),
        h("span", { class: "badge", text: link.availability }), icon("chev", 14))));
    });
  });
  return list;
}

function observationBlock(label, rows) {
  var box = h("div", { class: "card tinted card-sm stack gap-6" });
  box.appendChild(h("span", { class: "caption", text: label }));
  if (!rows.length) {
    box.appendChild(h("span", { class: "t-14-strong", text: "기록 없음" }));
    box.appendChild(h("span", { class: "caption", text: "이 조건은 해당 단계의 실행이 없습니다" }));
    return box;
  }
  rows.forEach(function (observation) {
    var mark = observation.result === "pass" ? "ready"
      : observation.result === "fail" ? "blocked" : "needs";
    var stroke = observation.result === "pass" ? "var(--ok-mark)"
      : observation.result === "fail" ? "var(--danger-mark)" : "var(--warn-mark)";
    box.appendChild(h("div", { class: "row gap-6 wrap-row" }, icon(mark, 14, stroke),
      h("span", { class: "t-14-strong nowrap", text: observation.result }),
      h("span", { class: "caption breakable", text: observation.test_id || "" })));
  });
  return box;
}

async function openDrawer(detail, claimId) {
  var token = routeToken;
  var result = await call("/snapshots/" + encodeURIComponent(detail.snapshot_key)
    + "/claims/" + encodeURIComponent(claimId));
  if (token !== routeToken) return;
  var overlay = document.getElementById("overlay");
  overlay.textContent = "";
  if (result.status !== 200 || !result.data) {
    overlay.appendChild(h("div", { class: "wrap" }, notice("blocked", errorText(result))));
    return;
  }
  var claim = result.data;
  drawerReturn = document.activeElement;

  var panel = h("aside", { class: "drawer", role: "dialog", "aria-modal": "true",
    "aria-label": "조건 상세: " + claim.text });
  var head = h("div", { class: "drawer-head" },
    h("span", { class: "caption grow", text: "조건 상세" }),
    h("button", { class: "icon-button push", "aria-label": "닫기",
      onclick: function () { closeDrawer(true); } }, icon("close", 16, "var(--ink-muted)")));
  panel.appendChild(head);

  var body = h("div", { class: "stack gap-16 pad-24" });
  body.appendChild(h("div", { class: "stack gap-8" },
    h("span", { class: "caption", text: claim.required ? "필수 조건" : "선택 조건" }),
    h("h2", { class: "card-title", text: claim.text }),
    h("div", { class: "row gap-8" }, claimTag(claim.status, 14),
      h("span", { class: "badge", text: "비교 기준 " + claim.comparison }))));

  if (!(claim.checks || []).length) {
    var legacyBox = h("div", { class: "stack gap-10" });
    legacyBox.appendChild(h("hr", { class: "sep" }));
    legacyBox.appendChild(h("p", { class: "caption",
      text: "상세 검사 항목은 이전 형식에서 기록되지 않았습니다. 아래는 저장된 Observation입니다." }));
    var observations = claimObservations(claim);
    var pairLegacy = h("div", { class: "ba" });
    pairLegacy.appendChild(observationBlock("변경 전",
      observations.filter(function (one) { return one.phase === "before"; })));
    pairLegacy.appendChild(observationBlock("변경 후",
      observations.filter(function (one) { return one.phase !== "before"; })));
    legacyBox.appendChild(pairLegacy);
    var keys = evidenceKeysOf(claim);
    legacyBox.appendChild(h("span", { class: "caption", text: "근거 " + keys.length + "건" }));
    legacyBox.appendChild(evidenceLinks(detail, observations));
    body.appendChild(legacyBox);
  }

  (claim.checks || []).forEach(function (check) {
    var section = h("div", { class: "stack gap-10" });
    section.appendChild(h("hr", { class: "sep" }));
    section.appendChild(h("div", { class: "row gap-8 wrap-row" },
      h("span", { class: "caption grow", text: check.statement || check.id }),
      claimTag(check.status)));
    if ((check.reason_codes || []).length) {
      section.appendChild(h("span", { class: "caption", text: check.reason_codes.join(", ") }));
    }
    var pair = h("div", { class: "ba" });
    pair.appendChild(observationBlock("변경 전", check.before || []));
    pair.appendChild(observationBlock("변경 후", check.after || []));
    section.appendChild(pair);
    (check.comparisons || []).forEach(function (comparison) {
      var kv = h("dl", { class: "kv" });
      [["실행 환경", comparison.environment], ["검사 의미", comparison.test_meaning],
       ["비교 가능", comparison.comparable === null ? "알 수 없음" : (comparison.comparable ? "예" : "아니오")],
       ["변경 전 기대", comparison.expected_before === null ? "기록 없음" : comparison.expected_before]
      ].forEach(function (row) {
        kv.appendChild(h("dt", { text: row[0] }));
        kv.appendChild(h("dd", { text: String(row[1]) }));
      });
      section.appendChild(kv);
    });
    section.appendChild(h("span", { class: "caption", text: "근거 " + (check.evidence_count || 0)
      + "건 (읽을 수 없음 " + (check.unavailable_evidence_count || 0) + ")" }));
    section.appendChild(evidenceLinks(detail, (check.after || []).concat(check.before || [])));
    body.appendChild(section);
  });
  body.appendChild(h("p", { class: "caption",
    text: "stdout·diff 같은 원문은 상세 근거 화면에서 " + CHUNK_LABEL + "KiB씩 나눠 확인합니다." }));
  panel.appendChild(body);

  overlay.appendChild(h("div", { class: "scrim", onclick: function () { closeDrawer(true); } }));
  overlay.appendChild(panel);
  document.addEventListener("keydown", drawerKeys, true);
  head.querySelector("button").focus();
  announce("조건 상세를 열었습니다.");
}

/* ---------- Detailed Evidence ---------- */

var FIELDS = [["command", "command"], ["stdout", "stdout"], ["stderr", "stderr"],
              ["diff", "diff"], ["raw", "raw"]];

function fieldPanel(key, evidenceKey, name, field) {
  var box = h("section", { class: "stack gap-8" });
  var head = h("div", { class: "row gap-8" }, h("h3", { class: "card-title t-15", text: name }));
  head.appendChild(h("span", { class: "badge", text: field.availability }));
  box.appendChild(head);
  if (field.availability !== "available" || field.text === null) {
    box.appendChild(h("div", { class: "card card-sm" },
      h("p", { class: "body-sm", text: field.reason_code
        ? "읽을 수 없습니다 (" + field.reason_code + ")" : "내용이 없습니다." })));
    return box;
  }
  var pane = h("pre", { class: "raw", tabindex: "0", text: field.text });
  box.appendChild(pane);
  var cursor = field.next_cursor;
  if (cursor) {
    var more = h("button", { class: "chip", text: "다음 " + CHUNK_LABEL + " KiB 보기" });
    more.addEventListener("click", async function () {
      more.disabled = true;
      var result = await call("/snapshots/" + encodeURIComponent(key) + "/evidence/"
        + encodeURIComponent(evidenceKey) + "/content?field=" + encodeURIComponent(name)
        + "&cursor=" + encodeURIComponent(cursor));
      more.disabled = false;
      if (result.status !== 200 || !result.data) {
        box.appendChild(notice("blocked", errorText(result)));
        more.remove();
        return;
      }
      if (result.data.availability !== "available" || result.data.text === null) {
        /* 이어 읽던 근거가 바뀌면 새 내용을 섞지 않고 멈춘다. */
        box.appendChild(notice("blocked",
          "이어 읽는 중 이 근거가 " + result.data.availability + " 상태가 됐습니다. "
          + "여기까지 표시한 부분은 지금 유효한 전체 근거가 아닙니다."));
        more.remove();
        return;
      }
      pane.appendChild(document.createTextNode(result.data.text));
      cursor = result.data.next_cursor;
      if (!cursor) more.remove();
    });
    box.appendChild(h("div", { class: "row gap-8 wrap-row" }, more,
      h("span", { class: "caption", text: "서버가 준 cursor로만 이어 읽습니다. 전체를 한 번에 받지 않습니다." })));
  }
  return box;
}

async function evidenceScreen(key, evidenceKey) {
  var token = routeToken;
  var result = await call("/snapshots/" + encodeURIComponent(key)
    + "/evidence/" + encodeURIComponent(evidenceKey));
  if (token !== routeToken) return;
  if (result.status === 401) { loginScreen(null); return; }
  crumbs([{ label: "검토 결과", hash: "/" },
          { label: "검토", hash: "/snapshots/" + encodeURIComponent(key) },
          { label: "근거 상세" }]);
  if (result.status !== 200 || !result.data) {
    paint(h("div", { class: "wrap stack gap-16" },
      h("a", { class: "link-row", href: "#/snapshots/" + encodeURIComponent(key) },
        icon("back", 13), h("span", { text: "검토로 돌아가기" })),
      notice("blocked", errorText(result))));
    return;
  }
  var evidence = result.data;
  var page = h("div", { class: "wrap stack gap-16" });
  page.appendChild(h("a", { class: "link-row", href: "#/snapshots/" + encodeURIComponent(key) },
    icon("back", 13), h("span", { text: "검토로 돌아가기" })));
  page.appendChild(h("div", { class: "stack gap-6" },
    h("h1", { class: "page-title t-24", text: "근거 상세" }),
    h("div", { class: "row gap-8 wrap-row" },
      h("span", { class: "badge", text: evidence.availability }),
      h("span", { class: "caption", text: (evidence.claim_id || "-") + " · " + (evidence.check_id || "-") }))));

  var meta = h("dl", { class: "kv" });
  Object.keys(evidence.metadata || {}).forEach(function (name) {
    var value = evidence.metadata[name];
    if (value === null || value === undefined) return;
    meta.appendChild(h("dt", { text: name }));
    meta.appendChild(h("dd", { text: String(value) }));
  });
  page.appendChild(h("section", { class: "stack gap-8" },
    h("h2", { class: "card-title t-15", text: "근거 metadata" }),
    h("div", { class: "card card-sm" }, meta)));

  var slots = {};
  FIELDS.forEach(function (pair) {
    var slot = h("section", { class: "stack gap-8" },
      h("div", { class: "row gap-8" }, h("h3", { class: "card-title t-15", text: pair[0] }),
        h("span", { class: "badge", text: "불러오는 중" })));
    slots[pair[0]] = slot;
    page.appendChild(slot);
  });
  paint(page);                       /* header and metadata are readable immediately */

  for (var i = 0; i < FIELDS.length; i += 1) {
    var name = FIELDS[i][0];
    var loaded = await call("/snapshots/" + encodeURIComponent(key) + "/evidence/"
      + encodeURIComponent(evidenceKey) + "/content?field=" + encodeURIComponent(name));
    if (token !== routeToken) return;
    var field = loaded.status === 200 && loaded.data
      ? loaded.data : { availability: "unsupported", text: null, reason_code: null, next_cursor: null };
    var slot = slots[name];
    slot.replaceWith(fieldPanel(key, evidenceKey, name, field));
    slots[name] = null;
  }
}

/* ---------- router ---------- */

function unesc(value) {
  try { return decodeURIComponent(value); } catch (error) { return value; }
}

function parseHash() {
  var raw = location.hash.replace(/^#/, "");
  var cut = raw.indexOf("?");
  var path = cut < 0 ? raw : raw.slice(0, cut);
  var search = cut < 0 ? "" : raw.slice(cut + 1);
  var segments = path.split("/").filter(Boolean).map(unesc);
  var query = {};
  new URLSearchParams(search).forEach(function (value, name) { query[name] = value; });
  return { segments: segments, query: query };
}

async function render() {
  routeToken += 1;
  stopPolls(false);
  document.getElementById("overlay").textContent = "";
  var route = parseHash();
  var segments = route.segments;
  document.getElementById("origin-note").textContent = location.host;
  if (segments[0] === "snapshots" && segments[1]) {
    if (segments[2] === "evidence" && segments[3]) {
      await evidenceScreen(segments[1], segments[3]);
      return;
    }
    await detailScreen(segments[1], segments[2] === "claims" ? segments[3] : null);
    return;
  }
  await listScreen({ filter: route.query.filter || "all", q: route.query.q || "" });
}

window.addEventListener("hashchange", function () {
  asked.clear();                 /* a real new view may ensure again */
  render();
});

render();          /* listScreen's own 401 branch shows the token screen */
