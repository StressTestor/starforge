"""The selection studio — a self-contained offline HTML page for inspecting a
candidate sweep instead of trusting one scalar.

Renders a compare grid where every candidate carries its raw scalar, its
per-subject de-biased score, a frontier badge, its rank within its own subject,
the metrics it leads on, and a bar per metric. Sort by de-biased quality / raw
scalar / subject, filter to the Pareto frontier, and pin/reject candidates into a
human-pins manifest you can export. Images are embedded (base64), so the page is
a single portable file. Output is deterministic: the same sweep yields the same
HTML, no timestamps in the body.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from html import escape

from PIL import Image

from starforge.selection import METRIC_KEYS, Ranked, rank, subject_scaled

_METRIC_LABEL = {
    "tonal_range": "tonal",
    "thirds": "thirds",
    "focal_balance": "focal",
    "ring_separation": "ring",
    "color_harmony": "color",
    "busy_penalty": "busy",
}


@dataclass(frozen=True)
class StudioCandidate:
    subject: str
    preset: str
    seed: int
    raw_total: float
    reasons: dict[str, float]
    image: Image.Image

    @property
    def key(self) -> str:
        return f"{self.subject}:{self.preset}:{self.seed}"


def _png_data_uri(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _bars(reasons: dict[str, float], scaled: dict[str, float]) -> str:
    rows = []
    for key in METRIC_KEYS:
        pct = max(0.0, min(1.0, scaled[key])) * 100.0
        rows.append(
            f'<div class="bar"><span class="bl">{_METRIC_LABEL[key]}</span>'
            f'<span class="bt"><span class="bf" style="width:{pct:.1f}%"></span></span>'
            f'<span class="bv">{reasons[key]:.0f}</span></div>'
        )
    return "".join(rows)


def _card(candidate: StudioCandidate, ranked: Ranked, scaled: dict[str, float]) -> str:
    why = " · ".join(_METRIC_LABEL.get(metric, metric) for metric in ranked.why)
    frontier = "★ frontier" if ranked.frontier else ""
    return (
        f'<article class="card" data-subject="{escape(candidate.subject)}" '
        f'data-norm="{ranked.norm_total:.5f}" data-raw="{ranked.raw_total:.4f}" '
        f'data-frontier="{1 if ranked.frontier else 0}" data-key="{escape(candidate.key)}">'
        f'<div class="thumb"><img loading="lazy" src="{_png_data_uri(candidate.image)}" '
        f'alt="{escape(candidate.subject)} {candidate.seed}">'
        f'<span class="badge subj">{escape(candidate.subject)} #{ranked.subject_rank}</span>'
        f'{f"<span class=\"badge front\">{frontier}</span>" if ranked.frontier else ""}</div>'
        f'<div class="body">'
        f'<div class="title">{escape(candidate.preset)} · seed {candidate.seed}</div>'
        f'<div class="scores"><span title="per-subject de-biased quality">norm '
        f"<b>{ranked.norm_total:.2f}</b></span>"
        f'<span title="raw v6 scalar">raw {ranked.raw_total:.0f}</span></div>'
        f'<div class="why">leads on <b>{escape(why)}</b></div>'
        f'<div class="bars">{_bars(candidate.reasons, scaled)}</div>'
        f'<div class="actions"><button class="pin" data-act="pin">pin</button>'
        f'<button class="rej" data-act="reject">reject</button></div>'
        f"</div></article>"
    )


def build_studio_page(
    candidates: list[StudioCandidate], *, title: str = "starforge studio", ranked: list[Ranked] | None = None
) -> str:
    if not candidates:
        raise ValueError("studio needs at least one candidate")

    rows = [c.reasons for c in candidates]
    subjects = [c.subject for c in candidates]
    # the caller (CLI) computes the ranking once and shares it for the manifest;
    # fall back to computing it here when called standalone.
    if ranked is None:
        ranked = rank(rows, subjects, raw_totals=[c.raw_total for c in candidates])
    scaled = subject_scaled(rows, subjects)

    # default presentation order: de-biased quality, then raw, then key (stable)
    order = sorted(
        range(len(candidates)),
        key=lambda i: (-ranked[i].norm_total, -ranked[i].raw_total, candidates[i].key),
    )
    cards = "".join(_card(candidates[i], ranked[i], scaled[i]) for i in order)

    subjects_present = sorted({c.subject for c in candidates})
    frontier_count = sum(1 for r in ranked if r.frontier)
    options = "".join(f'<option value="{escape(s)}">{escape(s)}</option>' for s in subjects_present)
    summary = (
        f"{len(candidates)} candidates · {frontier_count} on the frontier · "
        f"{len(subjects_present)} subjects"
    )

    return (
        _SHELL.replace("__TITLE__", escape(title))
        .replace("__SUMMARY__", summary)
        .replace("__OPTIONS__", options)
        .replace("__CARDS__", cards)
    )


_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{color-scheme:dark;--bg:#05070f;--panel:#0f1422;--line:#2c3c52;--text:#e9f6fb;--muted:#8fb6c6;--accent:#ff9a4d;--good:#54d18b;--front:#ffb347;}
*{box-sizing:border-box;}
body{margin:0;background:radial-gradient(circle at 50% -10%,#13203a 0,var(--bg) 55%,#01020a 100%);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Avenir Next",Inter,sans-serif;}
main{width:min(1320px,calc(100% - 28px));margin:0 auto;padding:22px 0 60px;}
header{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;margin-bottom:14px;}
h1{font-size:clamp(26px,4vw,42px);margin:0;letter-spacing:-.5px;}
.sum{color:var(--muted);}
.toolbar{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:12px 0;margin-bottom:14px;background:linear-gradient(var(--bg),color-mix(in srgb,var(--bg) 70%,transparent));border-bottom:1px solid var(--line);}
.toolbar label{color:var(--muted);}
select,button{font:inherit;color:var(--text);background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:7px 11px;cursor:pointer;}
button:hover{border-color:var(--accent);}
.toolbar .spacer{flex:1;}
.count{color:var(--muted);}
.count b{color:var(--good);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:16px;}
.card{border:1px solid var(--line);background:color-mix(in srgb,var(--panel) 86%,transparent);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;transition:border-color .15s,opacity .15s;}
.card.pinned{border-color:var(--good);box-shadow:0 0 0 1px var(--good) inset;}
.card.rejected{opacity:.32;filter:grayscale(.6);}
.thumb{position:relative;background:#02030a;}
.thumb img{display:block;width:100%;}
.badge{position:absolute;font-size:11px;font-weight:700;padding:3px 7px;border-radius:6px;background:rgba(5,7,15,.78);}
.badge.subj{left:8px;top:8px;color:var(--text);}
.badge.front{right:8px;top:8px;color:#1a1206;background:var(--front);}
.body{padding:11px 12px 12px;display:flex;flex-direction:column;gap:7px;}
.title{font-weight:700;}
.scores{display:flex;gap:12px;color:var(--muted);font-size:13px;}
.scores b{color:var(--text);font-size:15px;}
.why{color:var(--muted);font-size:12px;}
.why b{color:var(--accent);}
.bars{display:flex;flex-direction:column;gap:3px;margin-top:2px;}
.bar{display:grid;grid-template-columns:38px 1fr 30px;gap:6px;align-items:center;font-size:11px;color:var(--muted);}
.bt{height:7px;background:#0a1018;border-radius:4px;overflow:hidden;}
.bf{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--front));}
.bv{text-align:right;color:var(--text);}
.actions{display:flex;gap:8px;margin-top:3px;}
.actions button{flex:1;padding:6px;font-size:12px;}
.card.pinned .pin{border-color:var(--good);color:var(--good);}
.card.rejected .rej{border-color:var(--accent);color:var(--accent);}
.hidden{display:none !important;}
footer{margin-top:26px;color:var(--muted);font-size:12px;text-align:center;}
</style>
</head>
<body>
<main>
<header><h1>__TITLE__</h1><span class="sum">__SUMMARY__</span></header>
<div class="toolbar">
<label>sort <select id="sort">
<option value="norm">de-biased quality</option>
<option value="raw">raw scalar (v6)</option>
<option value="subject">by subject</option>
</select></label>
<label>subject <select id="subject"><option value="">all</option>__OPTIONS__</select></label>
<label><input type="checkbox" id="frontier"> frontier only</label>
<span class="spacer"></span>
<span class="count"><b id="pinCount">0</b> pinned</span>
<button id="export">export pins</button>
</div>
<div class="grid" id="grid">__CARDS__</div>
<footer>norm = each candidate scored against others of its own subject, so quality is not a contrast popularity contest. ★ frontier = non-dominated across all metrics. pins export as a manifest you can re-render.</footer>
</main>
<script>
(function(){
var grid=document.getElementById('grid');
var cards=Array.prototype.slice.call(grid.querySelectorAll('.card'));
var pinned=new Set(),rejected=new Set();
function applyFilter(){
var subj=document.getElementById('subject').value;
var frontOnly=document.getElementById('frontier').checked;
cards.forEach(function(c){
var ok=(!subj||c.dataset.subject===subj)&&(!frontOnly||c.dataset.frontier==='1');
c.classList.toggle('hidden',!ok);
});
}
function applySort(){
var mode=document.getElementById('sort').value;
var sorted=cards.slice().sort(function(a,b){
if(mode==='subject'){
var s=a.dataset.subject.localeCompare(b.dataset.subject);
if(s!==0)return s;
return parseFloat(b.dataset.norm)-parseFloat(a.dataset.norm);
}
var k=mode==='raw'?'raw':'norm';
return parseFloat(b.dataset[k])-parseFloat(a.dataset[k]);
});
sorted.forEach(function(c){grid.appendChild(c);});
}
grid.addEventListener('click',function(e){
var btn=e.target.closest('button[data-act]');if(!btn)return;
var card=btn.closest('.card'),key=card.dataset.key,act=btn.dataset.act;
if(act==='pin'){
if(pinned.has(key)){pinned.delete(key);card.classList.remove('pinned');}
else{pinned.add(key);rejected.delete(key);card.classList.add('pinned');card.classList.remove('rejected');}
}else{
if(rejected.has(key)){rejected.delete(key);card.classList.remove('rejected');}
else{rejected.add(key);pinned.delete(key);card.classList.add('rejected');card.classList.remove('pinned');}
}
document.getElementById('pinCount').textContent=pinned.size;
});
document.getElementById('export').addEventListener('click',function(){
var pins=[];
pinned.forEach(function(key){var p=key.split(':');pins.push({subject:p[0],preset:p[1],seed:parseInt(p[2],10)});});
pins.sort(function(a,b){return a.subject.localeCompare(b.subject)||a.preset.localeCompare(b.preset)||a.seed-b.seed;});
var blob=new Blob([JSON.stringify({pins:pins},null,2)],{type:'application/json'});
var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='starforge_pins.json';a.click();
});
['sort','subject','frontier'].forEach(function(id){document.getElementById(id).addEventListener('change',function(){applyFilter();applySort();});});
applySort();
})();
</script>
</body>
</html>
"""
