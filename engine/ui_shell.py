"""Shared WayFold Compliance application shell.

Visual source of truth: docs/design/wayfold-compliance-definitive-mockup.html
Identity: navy sidebar · light surfaces · WayFold purple · dense desktop-first GRC UI.
"""

from __future__ import annotations

from html import escape
from typing import Iterable
from urllib.parse import parse_qsl, urlencode

from engine.i18n import (
    DEFAULT_LANG,
    DEFAULT_NAV_KEYS,
    NAV_PROGRAM_SECTION,
    NAV_SECTIONS,
    normalize_lang,
    nav_labels,
    t,
    with_lang,
)
from engine.ui_icons import icon, icon_for_path, sprite_defs

WAYFOLD_CSS = """
:root{
  --wf-ink:#151b2b;--wf-ink-2:#242c3d;--wf-muted:#6f7a8e;--wf-muted-2:#96a0b2;
  --wf-bg:#f5f7fb;--wf-surface:#ffffff;--wf-surface-2:#fafbfc;--wf-surface-3:#f1f4f8;
  --wf-border:#e2e7ef;--wf-border-strong:#d5dbe5;
  --wf-sidebar:#101522;--wf-sidebar-2:#171d2b;--wf-sidebar-text:#c9d0dc;--wf-sidebar-muted:#768196;
  --wf-primary:#675cf2;--wf-primary-hover:#564be3;--wf-primary-soft:#f0efff;--wf-primary-soft-2:#e8e6ff;
  --wf-success:#17834b;--wf-success-soft:#ebf7f0;
  --wf-warning:#a76308;--wf-warning-soft:#fff5df;
  --wf-danger:#b42318;--wf-danger-soft:#fff0ef;
  --wf-info:#2563d8;--wf-info-soft:#edf4ff;
  --wf-violet:#7c3aed;--wf-violet-soft:#f5f0ff;
  --wf-cyan:#0f7490;--wf-cyan-soft:#e9f8fb;
  --wf-shadow-xs:0 1px 2px rgba(16,24,40,.035);
  --wf-shadow-sm:0 6px 20px rgba(21,27,43,.045),0 1px 2px rgba(21,27,43,.035);
  --wf-shadow-md:0 22px 60px rgba(21,27,43,.14);
  --wf-r-sm:8px;--wf-r:12px;--wf-r-lg:16px;
  --wf-font:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --wf-mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  /* aliases used by older page markup */
  --bg:var(--wf-bg);--srf:var(--wf-surface);--srf2:var(--wf-surface-2);
  --ink:var(--wf-ink);--ink2:var(--wf-ink-2);--mut:var(--wf-muted);
  --line:var(--wf-border);--line2:var(--wf-border-strong);
  --acc:var(--wf-primary);--acc-h:var(--wf-primary-hover);--acc-soft:var(--wf-primary-soft);
  --ok:var(--wf-success);--ok-soft:var(--wf-success-soft);
  --warn:var(--wf-warning);--warn-soft:var(--wf-warning-soft);
  --danger:var(--wf-danger);--danger-soft:var(--wf-danger-soft);
  --r-s:var(--wf-r-sm);--r-m:var(--wf-r);--r-l:var(--wf-r-lg);
  --sh-s:var(--wf-shadow-sm);--sh-m:var(--wf-shadow-md);
  --sans:var(--wf-font);--mono:var(--wf-mono);--display:var(--wf-font);
  color-scheme:light;
}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{
  font-family:var(--wf-font);color:var(--wf-ink);background:var(--wf-bg);
  font-size:14px;line-height:1.45;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}
button,input,select,textarea{font:inherit;color:inherit}
button{cursor:pointer}
svg{display:block}
a{color:inherit;text-decoration:none}
a:hover{color:var(--wf-primary)}
.hidden-svg{position:absolute;width:0;height:0;overflow:hidden}
.wf-icon,.nav-icon{width:17px;height:17px;flex:0 0 auto}
:focus-visible{outline:2px solid var(--wf-primary);outline-offset:2px}

.shell{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}
.sidebar{
  position:sticky;top:0;height:100vh;z-index:40;display:flex;flex-direction:column;
  background:radial-gradient(circle at 35% -10%,rgba(103,92,242,.16),transparent 26%),
    linear-gradient(180deg,var(--wf-sidebar) 0%,#0d121d 100%);
  border-right:1px solid rgba(255,255,255,.045);
}
.brand{height:70px;padding:0 18px;display:flex;align-items:center;gap:11px;border-bottom:1px solid rgba(255,255,255,.065)}
.brand-mark{
  width:34px;height:34px;border-radius:10px;background:linear-gradient(145deg,#7a71ff,#5a4ff0);
  display:grid;place-items:center;color:#fff;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.18),0 5px 16px rgba(77,66,211,.26);
}
.brand-mark .wf-icon{width:20px;height:20px;color:#fff}
.brand-title{font-size:14px;font-weight:700;color:#fff;letter-spacing:-.01em}
.brand-sub{font-size:11px;color:#7e899e;margin-top:1px}
.nav-wrap{flex:1 1 auto;min-height:0;padding:14px 10px;overflow-y:auto;overflow-x:hidden}
.nav-section{margin-bottom:18px}
.program-context{
  margin:0 10px 12px;padding:10px 12px;border-radius:10px;
  background:rgba(103,92,242,.14);border:1px solid rgba(132,124,255,.22);color:#e8e6ff
}
.program-context .pc-client{font-size:12px;font-weight:750;color:#fff;line-height:1.3}
.program-context .pc-program{font-size:11px;color:#b9c0d0;margin-top:2px}
code,.control-code,td code{white-space:nowrap}
.dropdown{position:relative}
.dropdown-menu{
  display:none;position:absolute;right:0;top:calc(100% + 6px);min-width:220px;z-index:50;
  background:#fff;border:1px solid var(--wf-border);border-radius:12px;box-shadow:var(--wf-shadow-md);padding:6px
}
.dropdown.open .dropdown-menu{display:block}
.dropdown-menu a{
  display:block;padding:9px 12px;border-radius:8px;font-size:13px;font-weight:600;color:var(--wf-ink)
}
.dropdown-menu a:hover{background:var(--wf-primary-soft);color:var(--wf-primary)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.form-grid .full{grid-column:1/-1}
.form-field label{display:block;font-size:12px;font-weight:650;color:var(--wf-muted);margin-bottom:5px}
.form-field input,.form-field select,.form-field textarea{
  width:100%;border:1px solid var(--wf-border);border-radius:9px;padding:9px 11px;background:#fff
}
.form-field textarea{min-height:90px;resize:vertical}
.tabs{display:flex;gap:4px;flex-wrap:wrap;margin:0 0 14px;border-bottom:1px solid var(--wf-border)}
.tabs a,.tabs button{
  border:0;background:transparent;padding:10px 12px;font-weight:650;color:var(--wf-muted);border-bottom:2px solid transparent
}
.tabs a.active,.tabs button.active{color:var(--wf-primary);border-bottom-color:var(--wf-primary)}
@media(max-width:900px){.form-grid{grid-template-columns:1fr}}
.nav-label{
  padding:4px 10px 7px;color:#667287;font-size:10px;font-weight:700;
  letter-spacing:.12em;text-transform:uppercase
}
.nav-item{
  width:100%;height:38px;padding:0 10px;border:0;border-radius:9px;background:transparent;
  color:var(--wf-sidebar-text);display:flex;align-items:center;gap:10px;text-align:left;
  transition:background .16s ease,color .16s ease;position:relative;text-decoration:none;
  font-size:12px;font-weight:600;margin-bottom:2px;
}
.nav-item:hover{background:rgba(255,255,255,.052);color:#fff}
.nav-item.active{background:linear-gradient(90deg,rgba(103,92,242,.18),rgba(103,92,242,.095));color:#fff}
.nav-item.active:before{
  content:"";position:absolute;left:0;top:8px;bottom:8px;width:2px;border-radius:3px;background:#847cff
}
.nav-item .nav-icon{color:#8f9aae}
.nav-item.active .nav-icon,.nav-item:hover .nav-icon{color:#dddafe}
.nav-text{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sidebar-footer{padding:13px 12px;border-top:1px solid rgba(255,255,255,.065)}
.lang-switch{
  width:100%;height:34px;border-radius:9px;border:1px solid rgba(255,255,255,.08);
  background:rgba(255,255,255,.04);color:#c9d0dc;display:flex;align-items:center;justify-content:center;gap:8px;
  font-size:11px;font-weight:650
}
.lang-switch:hover{background:rgba(255,255,255,.07);color:#fff}
.lang-switch .wf-icon{width:14px;height:14px}

.main{min-width:0;display:flex;flex-direction:column}
.topbar{
  position:sticky;top:0;z-index:35;height:64px;padding:0 26px;
  background:rgba(255,255,255,.92);backdrop-filter:blur(14px);
  border-bottom:1px solid rgba(226,231,239,.92);display:flex;align-items:center;gap:16px
}
.breadcrumb{display:flex;align-items:center;gap:7px;color:var(--wf-muted);font-size:12px}
.breadcrumb .wf-icon{width:13px;height:13px;color:#a3abba}
.breadcrumb strong{font-weight:700;color:var(--wf-ink)}
.topbar-actions{margin-left:auto;display:flex;gap:8px;align-items:center}
.icon-btn{
  width:36px;height:36px;border:1px solid var(--wf-border);border-radius:9px;background:#fff;color:#667085;
  display:grid;place-items:center;transition:.15s;box-shadow:var(--wf-shadow-xs)
}
.icon-btn:hover{background:#f8fafc;color:var(--wf-ink);border-color:var(--wf-border-strong)}
.icon-btn .wf-icon{width:16px;height:16px}
.content{padding:26px 28px 44px;max-width:1700px;margin:0 auto;width:100%}

.page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:20px}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--wf-muted);margin-bottom:6px}
h1{font-size:26px;line-height:1.18;margin:0;letter-spacing:-.03em;font-weight:750}
h2{font-size:15px;font-weight:700;margin:1.4rem 0 .55rem;letter-spacing:-.01em}
.subtitle,.meta,.hint{max-width:850px;margin:.45rem 0 0;color:var(--wf-muted);font-size:13px;line-height:1.55}
.page-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}

.btn{
  height:36px;padding:0 12px;border:1px solid var(--wf-border-strong);border-radius:9px;background:#fff;
  color:#3c4658;font-size:12px;font-weight:650;display:inline-flex;align-items:center;gap:7px;
  box-shadow:var(--wf-shadow-xs);text-decoration:none
}
.btn:hover{background:#f9fafc;border-color:#cbd3df;color:var(--wf-ink);text-decoration:none}
.btn .wf-icon{width:14px;height:14px}
.btn.primary{background:var(--wf-primary);border-color:var(--wf-primary);color:#fff}
.btn.primary:hover{background:var(--wf-primary-hover);color:#fff}
.btn.ghost{border-color:transparent;background:transparent;box-shadow:none;color:var(--wf-muted)}
.btn.danger{color:var(--wf-danger);background:var(--wf-danger-soft);border-color:#ffd8d5}
.btn.sm{height:30px;padding:0 9px;font-size:11px}
button:not(.nav-item):not(.icon-btn):not(.lang-switch):not(.btn){
  height:36px;padding:0 12px;border:1px solid var(--wf-primary);border-radius:9px;
  background:var(--wf-primary);color:#fff;font-size:12px;font-weight:650
}
button:not(.nav-item):not(.icon-btn):not(.lang-switch):not(.btn):hover{background:var(--wf-primary-hover)}

.grid{display:grid;gap:14px}
.grid-4{grid-template-columns:repeat(4,minmax(0,1fr))}
.grid-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.grid-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.split-main{display:grid;grid-template-columns:minmax(0,1.57fr) minmax(300px,.73fr);gap:14px}
.stack{display:grid;gap:14px}

.panel,.card,.table-wrap{
  background:var(--wf-surface);border:1px solid var(--wf-border);border-radius:var(--wf-r);
  box-shadow:var(--wf-shadow-sm);overflow:hidden
}
.panel-head{
  min-height:52px;padding:0 15px;border-bottom:1px solid var(--wf-border);
  display:flex;align-items:center;gap:10px
}
.panel-title{font-size:13px;font-weight:720}
.panel-subtitle{font-size:11px;color:var(--wf-muted);margin-top:2px}
.panel-head-spacer{margin-left:auto}
.panel-body{padding:15px}
.panel-toolbar{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.metric{padding:16px 17px;min-height:108px;position:relative;overflow:hidden}
.metric:after{
  content:"";position:absolute;right:-25px;bottom:-28px;width:82px;height:82px;border-radius:50%;
  border:16px solid var(--wf-primary-soft);opacity:.8
}
.metric-icon{
  width:28px;height:28px;border-radius:8px;background:var(--wf-primary-soft);color:var(--wf-primary);
  display:grid;place-items:center;margin-bottom:11px
}
.metric-icon .wf-icon{width:14px;height:14px}
.metric-label{font-size:11px;color:var(--wf-muted);font-weight:650}
.metric-value{font-size:26px;letter-spacing:-.04em;font-weight:750;margin-top:3px}
.metric-footer{font-size:11px;color:var(--wf-muted);margin-top:6px}
.text-success{color:var(--wf-success);font-weight:700}
.text-warning{color:var(--wf-warning);font-weight:700}
.text-danger{color:var(--wf-danger);font-weight:700}
.text-primary{color:var(--wf-primary);font-weight:700}

.badge{
  display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:999px;
  font-size:11px;font-weight:700;white-space:nowrap;line-height:1;border:1px solid transparent
}
.badge-dot{width:5px;height:5px;border-radius:50%;background:currentColor}
.badge.success,.badge.ok{color:var(--wf-success);background:var(--wf-success-soft)}
.badge.warning,.badge.warn{color:var(--wf-warning);background:var(--wf-warning-soft)}
.badge.danger{color:var(--wf-danger);background:var(--wf-danger-soft)}
.badge.info{color:var(--wf-info);background:var(--wf-info-soft)}
.badge.violet{color:var(--wf-violet);background:var(--wf-violet-soft)}
.badge.neutral{color:#5f697b;background:#eef1f5}
.badge.cyan{color:var(--wf-cyan);background:var(--wf-cyan-soft)}

.progress{height:6px;background:#edf0f4;border-radius:999px;overflow:hidden}
.progress>span{display:block;height:100%;border-radius:inherit;background:var(--wf-primary)}
.progress.success>span{background:#24a360}
.progress.warning>span{background:#dfa12b}
.progress.danger>span{background:#d34a40}

.filters,.table-toolbar{
  display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px;align-items:end;
  padding:12px;background:var(--wf-surface);border:1px solid var(--wf-border);border-radius:var(--wf-r);
  box-shadow:var(--wf-shadow-sm)
}
.filters label{
  display:flex;flex-direction:column;font-size:10px;color:var(--wf-muted);gap:4px;
  font-weight:700;letter-spacing:.04em;text-transform:uppercase
}
.filters input,.filters select,.filter-input,.filter-select{
  height:32px;border:1px solid var(--wf-border);border-radius:8px;background:#fff;
  outline:0;padding:0 9px;font-size:12px;color:#586477;min-width:8rem
}
.filters input:focus,.filters select:focus,.filter-input:focus,.filter-select:focus{
  border-color:#beb8ff;box-shadow:0 0 0 3px rgba(103,92,242,.08)
}

.table-wrap{overflow:auto;-webkit-overflow-scrolling:touch;margin:0 0 1.1rem}
table,.data-table{border-collapse:collapse;width:100%;min-width:720px;font-size:12.5px}
th,td{border-bottom:1px solid var(--wf-border);padding:11px 12px;vertical-align:middle;text-align:left}
th{
  background:var(--wf-surface-2);color:var(--wf-muted);font-size:10px;font-weight:750;
  letter-spacing:.07em;text-transform:uppercase;white-space:nowrap;position:sticky;top:0;z-index:1
}
td{color:var(--wf-ink-2)}
tr:last-child td{border-bottom:0}
tbody tr:hover td{background:#fbfcff}
code,pre{font-family:var(--wf-mono);font-size:12px}
code{background:var(--wf-surface-3);padding:.12rem .38rem;border-radius:6px;border:1px solid var(--wf-border);color:var(--wf-primary)}
pre.diff{background:#0f1420;color:#e8efe9;padding:1rem;border-radius:var(--wf-r-sm);overflow:auto;max-height:22rem;font-size:.75rem}
.diff-add{display:block;background:#edf8f1;color:#24683f;padding:1px 4px;border-radius:3px;margin:2px 0}
.diff-del{display:block;background:#fff0ef;color:#9c2d24;padding:1px 4px;border-radius:3px;margin:2px 0}
ul.compact{margin:.25rem 0 .9rem 1.15rem;padding:0}
.warn,.overdue{color:var(--wf-danger);font-weight:650}
section{margin:1.25rem 0}
.control-code{font-size:11px;font-weight:750;color:var(--wf-primary);letter-spacing:.02em}
.control-title{font-size:13px;font-weight:700;margin-top:2px}
.control-desc{font-size:12px;color:var(--wf-muted);margin-top:3px;max-width:420px;line-height:1.45}
.coverage-list{display:flex;gap:4px;flex-wrap:wrap}
.coverage-pill{
  display:inline-flex;padding:3px 6px;border-radius:5px;font-size:10px;font-weight:750;border:1px solid
}
.coverage-pill.full{color:var(--wf-success);background:#eff9f3;border-color:#d4eddd}
.coverage-pill.partial{color:var(--wf-warning);background:#fff8e9;border-color:#f3dfb7}
.coverage-pill.support{color:var(--wf-violet);background:#f6f2ff;border-color:#e5dcff}
.framework-chips{display:flex;gap:4px;flex-wrap:wrap}
.framework-chip{
  padding:3px 6px;border-radius:5px;border:1px solid var(--wf-border);background:#fff;color:#5f697a;
  font-size:10px;font-weight:700
}
.readiness-cell{display:grid;grid-template-columns:40px 1fr;gap:8px;align-items:center}
.client-cell{display:flex;align-items:center;gap:10px;min-width:0}
.client-logo{
  width:34px;height:34px;border-radius:9px;display:grid;place-items:center;background:#eef1f7;color:#515d70;
  font-size:11px;font-weight:750;flex:0 0 auto
}
.client-name{font-size:13px;font-weight:700}
.client-meta{font-size:11px;color:var(--wf-muted);margin-top:2px}
.row-action{
  width:28px;height:28px;border:1px solid var(--wf-border);border-radius:8px;background:#fff;color:#798396;
  display:inline-grid;place-items:center
}
.row-action:hover{color:var(--wf-primary);border-color:#cfcafc;background:#f8f7ff}
.row-action .wf-icon{width:13px;height:13px}
.gap-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin-bottom:14px}
.gap-stat{padding:12px;border:1px solid var(--wf-border);border-radius:9px;background:#fbfcfe}
.gap-stat-label{font-size:11px;color:var(--wf-muted)}
.gap-stat-value{font-size:18px;font-weight:750;margin-top:2px}
.client-summary{
  display:flex;align-items:center;gap:12px;padding:13px 15px;background:#fff;border:1px solid var(--wf-border);
  border-radius:12px;box-shadow:var(--wf-shadow-sm);margin-bottom:14px
}
.framework-card{padding:14px;border:1px solid var(--wf-border);border-radius:12px;background:#fff}
.framework-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:13px}
.mini-stat{padding:8px;border-radius:8px;background:#f7f8fa}
.mini-stat strong{font-size:14px;display:block}
.mini-stat span{font-size:10px;color:var(--wf-muted);margin-top:1px;display:block}
.mapping-strip{
  padding:13px 14px;display:grid;grid-template-columns:minmax(210px,1fr) 38px minmax(220px,1fr) 140px;
  gap:12px;align-items:center;border-bottom:1px solid var(--wf-border)
}
.mapping-node{padding:10px;border:1px solid var(--wf-border);border-radius:9px;background:#fbfcfe}
.mapping-arrow{display:grid;place-items:center;color:#9ba4b3}
.empty-state{padding:36px 20px;text-align:center;color:var(--wf-muted)}
.empty-icon{width:40px;height:40px;margin:0 auto 12px;border-radius:10px;background:var(--wf-surface-3);
  display:grid;place-items:center;color:var(--wf-muted)}
.empty-title{font-size:15px;font-weight:700;color:var(--wf-ink);margin-bottom:6px}
.empty-body{font-size:13px;max-width:42ch;margin:0 auto}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.field label{display:block;font-size:10px;font-weight:750;text-transform:uppercase;letter-spacing:.07em;color:var(--wf-muted);margin-bottom:4px}
.field-value{font-size:13px;font-weight:600}
.text-box{padding:10px;border:1px solid var(--wf-border);border-radius:8px;background:#fff;font-size:12.5px;line-height:1.55}
.mapping-card{padding:10px;border:1px solid var(--wf-border);border-radius:8px;margin-bottom:8px;background:#fff}
.mapping-delta{margin-top:8px;padding:8px;border-radius:7px;background:var(--wf-warning-soft);color:#86550e;font-size:12px;line-height:1.5}
.report-preview{
  width:min(780px,100%);margin:0 auto;background:#fff;border:1px solid var(--wf-border);border-radius:12px;
  box-shadow:0 14px 35px rgba(20,27,43,.07);padding:28px
}

@media(max-width:1300px){
  .grid-4{grid-template-columns:repeat(2,minmax(0,1fr))}
  .split-main{grid-template-columns:1fr}
  .gap-summary{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:980px){
  .shell{grid-template-columns:72px minmax(0,1fr)}
  .brand{padding:0;justify-content:center}
  .brand-copy,.nav-text,.nav-label{display:none}
  .nav-item{justify-content:center;padding:0}
  .content{padding:20px 18px 40px}
  .topbar{padding:0 18px}
  .detail-grid{grid-template-columns:1fr}
}
@media(max-width:720px){
  .grid-4,.grid-3,.grid-2{grid-template-columns:1fr}
  .page-head{flex-direction:column}
  .gap-summary{grid-template-columns:repeat(2,1fr)}
  table,.data-table{min-width:640px}
}
"""

SHELL_JS = """
function wfToggleLang(next){
  var u=new URL(window.location.href);
  u.searchParams.set('lang',next);
  window.location.href=u.toString();
}
function wfToggleTheme(){}
function wfToggleDropdown(id){
  var el=document.getElementById(id);
  if(!el) return;
  el.classList.toggle('open');
}
document.addEventListener('click',function(e){
  document.querySelectorAll('.dropdown.open').forEach(function(d){
    if(!d.contains(e.target)) d.classList.remove('open');
  });
});
"""

# Back-compat alias used by older imports/tests
DEFAULT_NAV = tuple((k.split(".", 1)[-1].title().replace("_", " "), p) for k, p in DEFAULT_NAV_KEYS)


def render_shell(
    title: str,
    nav_qs: str,
    body: str,
    *,
    nav_items: Iterable[tuple[str, str]] | None = None,
    nav_keys: Iterable[tuple[str, str]] | None = None,
    brand_subtitle: str = "Compliance",
    lang: str | None = None,
    active_path: str | None = None,
    breadcrumb: str | None = None,
    program_context: dict | None = None,
    can_quick_create: bool = True,
) -> str:
    lang = normalize_lang(lang or _lang_from_nav_qs(nav_qs))
    nav_qs = with_lang(nav_qs, lang)
    q = f"?{nav_qs}" if nav_qs else ""
    active = active_path or _guess_active_path(title, nav_keys)
    ctx = program_context or _program_context_from_qs(nav_qs)

    nav_html = _render_nav(
        lang=lang,
        q=q,
        active=active,
        nav_keys=tuple(nav_keys) if nav_keys is not None else None,
        nav_items=list(nav_items) if nav_items is not None else None,
        program_context=ctx,
    )

    page_title = title if "WayFold" in title else f"{title} — WayFold Compliance"
    crumb = breadcrumb or _breadcrumb_label(title, lang)
    brand_sub = escape(t(lang, "brand.sub"))
    quick_html = _quick_create_menu(lang, nav_qs) if can_quick_create else ""
    ctx_banner = ""
    if ctx and ctx.get("tenant_name"):
        ctx_banner = (
            f'<div class="program-context">'
            f'<div class="pc-client">{escape(str(ctx.get("tenant_name")))}</div>'
            f'<div class="pc-program">{escape(str(ctx.get("program_name") or ""))}</div>'
            f"</div>"
        )

    return f"""<!doctype html>
<html lang="{escape(lang)}"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="application-name" content="WayFold Compliance">
<title>{escape(page_title)}</title>
<script>{SHELL_JS}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{WAYFOLD_CSS}</style>
</head><body>
{sprite_defs()}
<div class="shell">
  <aside class="sidebar" aria-label="Navigazione principale">
    <a class="brand" href="/portfolio{q}">
      <div class="brand-mark">{icon("logo")}</div>
      <div class="brand-copy">
        <div class="brand-title">WayFold {escape(brand_subtitle)}</div>
        <div class="brand-sub">{brand_sub}</div>
      </div>
    </a>
    {ctx_banner}
    <nav class="nav-wrap">{nav_html}</nav>
    <div class="sidebar-footer">
      <a class="lang-switch" href="/logout" style="text-decoration:none" aria-label="{escape(t(lang, 'nav.logout'))}">
        {icon("x")}<span>{escape(t(lang, 'nav.logout'))}</span>
      </a>
    </div>
  </aside>
  <div class="main">
    <header class="topbar">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <span>WayFold</span>
        {icon("chevron-right")}
        <strong>{escape(crumb)}</strong>
      </nav>
      <div class="topbar-actions">{quick_html}</div>
    </header>
    <main class="content">
{body}
    </main>
  </div>
</div>
</body></html>"""


def _render_nav(
    *,
    lang: str,
    q: str,
    active: str | None,
    nav_keys: tuple[tuple[str, str], ...] | None,
    nav_items: list[tuple[str, str]] | None,
    program_context: dict | None = None,
) -> str:
    if nav_items is not None:
        return _flat_nav(nav_items, q, active)
    if nav_keys is not None:
        items = nav_labels(lang, nav_keys)
        return _flat_nav(items, q, active)

    parts: list[str] = []
    for section_key, entries in NAV_SECTIONS:
        # Insert program section after workspace when context is present
        if section_key == "nav.section.knowledge" and program_context and program_context.get("program_id"):
            parts.append(_nav_section_html(lang, q, active, *NAV_PROGRAM_SECTION))
        parts.append(_nav_section_html(lang, q, active, section_key, entries))
    return "".join(parts)


def _nav_section_html(
    lang: str,
    q: str,
    active: str | None,
    section_key: str,
    entries: tuple[tuple[str, str, str], ...],
) -> str:
    links = []
    for label_key, path, _icon_key in entries:
        label = t(lang, label_key)
        href_path = path.split("?", 1)[0]
        cls = "nav-item active" if _is_active(active, href_path) else "nav-item"
        # Preserve extra query on path (e.g. settings?tab=users) then append nav_qs
        if "?" in path:
            base, extra = path.split("?", 1)
            href = f"{escape(base)}?{extra}&{q.lstrip('?')}" if q else f"{escape(base)}?{extra}"
        else:
            href = f"{escape(path)}{q}"
        links.append(
            f'<a class="{cls}" href="{href}">'
            f"{icon_for_path(href_path)}"
            f'<span class="nav-text">{escape(label)}</span></a>'
        )
    return (
        f'<div class="nav-section">'
        f'<div class="nav-label">{escape(t(lang, section_key))}</div>'
        f'{"".join(links)}</div>'
    )


def _program_context_from_qs(nav_qs: str) -> dict | None:
    data = dict(parse_qsl(nav_qs or "", keep_blank_values=False))
    pid = data.get("program_id")
    if not pid:
        return None
    return {
        "program_id": pid,
        "tenant_name": data.get("tenant_name") or data.get("client_name") or "",
        "program_name": data.get("program_name") or "",
    }


def _quick_create_menu(lang: str, nav_qs: str) -> str:
    q = f"?{nav_qs}" if nav_qs else ""
    items = [
        ("quick.client", "/clients/new"),
        ("quick.program", "/programs/new"),
        ("quick.framework", "/frameworks/new"),
        ("quick.version", "/frameworks/versions/new"),
        ("quick.requirement", "/frameworks/requirements/new"),
        ("quick.control", "/controls/new"),
        ("quick.mapping", "/mappings/new"),
        ("quick.evidence", f"/evidence/new{q}"),
        ("quick.task", f"/tasks/new{q}"),
    ]
    links = "".join(
        f'<a href="{escape(path)}">{escape(t(lang, key))}</a>' for key, path in items
    )
    return f"""
<div class="dropdown" id="wf-quick-create">
  <button type="button" class="btn primary sm" onclick="wfToggleDropdown('wf-quick-create')">{escape(t(lang, 'quick.new'))}</button>
  <div class="dropdown-menu" role="menu">{links}</div>
</div>"""


def _flat_nav(items: list[tuple[str, str]], q: str, active: str | None) -> str:
    links = []
    for label, path in items:
        cls = "nav-item active" if _is_active(active, path) else "nav-item"
        links.append(
            f'<a class="{cls}" href="{escape(path)}{q}">'
            f'{icon_for_path(path)}'
            f'<span class="nav-text">{escape(label)}</span></a>'
        )
    return f'<div class="nav-section">{"".join(links)}</div>'


def _is_active(active: str | None, path: str) -> bool:
    if not active:
        return False
    a = active.rstrip("/") or "/"
    p = path.rstrip("/") or "/"
    if a == p:
        return True
    # group related routes
    if p == "/changes" and a in {"/change", "/changes", "/sources"}:
        return a == "/changes" or (a == "/change" and p == "/changes")
    if p == "/ai/suggestions" and a.startswith("/ai/"):
        return p == a
    return False


def _guess_active_path(title: str, nav_keys: Iterable[tuple[str, str]] | None) -> str | None:
    if nav_keys:
        # first key often current context; leave unset
        return None
    return None


def _breadcrumb_label(title: str, lang: str) -> str:
    cleaned = title.replace(" — WayFold Compliance", "").replace("WayFold Compliance", "").strip(" —")
    return cleaned or t(lang, "nav.portfolio")


def _lang_from_nav_qs(nav_qs: str) -> str:
    data = dict(parse_qsl(nav_qs or "", keep_blank_values=False))
    return normalize_lang(data.get("lang", DEFAULT_LANG))


def table_wrap(inner_table_html: str) -> str:
    return f'<div class="table-wrap">{inner_table_html}</div>'


def ensure_lang_in_qs(nav_qs: str, lang: str | None = None) -> str:
    lang = normalize_lang(lang or _lang_from_nav_qs(nav_qs))
    data = dict(parse_qsl(nav_qs, keep_blank_values=False))
    data["lang"] = lang
    return urlencode(data)
