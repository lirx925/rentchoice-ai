"""Narrative presentation layer for the RentChoice AI experiment.

The interface uses a quiet, single-scene rhythm inspired by interactive
explainers: one idea, one action, then the next scene.  Experiment logic and
saved data remain in ``app.py`` and the other ``src`` modules.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------
# Theme / CSS
# --------------------------------------------------------------------------

GAME_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#fff8e8; --paper-2:#f3e3bd; --ink:#604a32; --muted:#86735d;
  --line:#c7a977; --accent:#efb84a; --accent-soft:#fbe8b9; --green:#78994e;
  --mist:var(--muted); --amber:var(--accent); --coral:var(--accent);
}
.stApp{background:radial-gradient(circle at 50% 0,#fffdf4 0,#fff8e8 55%,#f6e8c9 100%); color:var(--ink);}
[data-testid="stHeader"]{display:none!important}
[data-testid="stToolbar"]{display:none!important}
[data-testid="stDecoration"]{display:none!important}
.stAppViewContainer{padding-top:0!important}
.block-container{max-width:1120px; padding-top:1.1rem; padding-bottom:4.5rem;}
h1,h2,h3,h4,p,span,label,.stMarkdown{color:var(--ink); font-family:'Noto Sans SC',sans-serif;}
.pxl{font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif; color:var(--ink); letter-spacing:2px;}
.narrative-stage{min-height:65vh; display:flex; flex-direction:column; justify-content:center; text-align:center; animation:scenein .48s cubic-bezier(.2,.8,.2,1);}
.island-cover{height:calc(100vh - 2.2rem);min-height:650px;border:0;border-radius:28px;overflow:hidden;background-position:center;background-size:cover;position:relative;box-shadow:0 16px 45px rgba(54,90,99,.18);display:flex;align-items:flex-start;justify-content:center;isolation:isolate;animation:coverReveal .7s ease-out both,oceanBreath 12s ease-in-out .7s infinite}.island-cover:before{content:'';position:absolute;inset:-8%;z-index:0;background:radial-gradient(circle at 50% 12%,rgba(255,255,232,.3),transparent 30%);animation:sunGlow 6s ease-in-out infinite}.island-cover:after{content:'';position:absolute;inset:0;z-index:0;background:linear-gradient(180deg,rgba(255,255,238,.03) 0%,transparent 46%,rgba(22,115,153,.08) 100%);pointer-events:none}.cover-copy{position:relative;z-index:2;margin-top:clamp(36px,7vh,78px);width:min(760px,88%);text-align:center;animation:titleFloat 4.8s ease-in-out infinite}.cover-copy:after{content:'✦';position:absolute;right:8%;top:-8px;color:#fff6c4;font-size:clamp(1.1rem,2vw,1.8rem);text-shadow:0 0 14px #fff;animation:twinkle 2.4s ease-in-out infinite}
.narrative-kicker{font-size:.78rem; letter-spacing:.22em; color:var(--accent); font-weight:700; text-transform:uppercase;}
.narrative-title{font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif;font-size:clamp(4.5rem,9vw,7.8rem);font-weight:900;line-height:1;margin:0;letter-spacing:.01em;filter:drop-shadow(0 8px 2px rgba(95,65,30,.2));white-space:nowrap}.title-orange{color:#ee6f37;text-shadow:-5px -5px 0 #fff8dc,5px -5px 0 #fff8dc,-5px 5px 0 #fff8dc,5px 5px 0 #fff8dc,0 7px 0 #b94e2d}.title-gold{color:#bd7f37;text-shadow:-5px -5px 0 #fff8dc,5px -5px 0 #fff8dc,-5px 5px 0 #fff8dc,5px 5px 0 #fff8dc,0 7px 0 #8a5c2e}.title-green{color:#7f963f;text-shadow:-5px -5px 0 #fff8dc,5px -5px 0 #fff8dc,-5px 5px 0 #fff8dc,5px 5px 0 #fff8dc,0 7px 0 #52692c}.narrative-subtitle{display:inline-block;margin:20px auto 0;padding:9px 42px 12px;border-radius:13px;background:linear-gradient(180deg,#c98543,#a85f2f);border:3px solid #8a4c27;box-shadow:0 6px 0 #774322,0 9px 20px rgba(75,48,23,.18);font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif;font-size:clamp(1.45rem,2.6vw,2.2rem);letter-spacing:.12em;color:#fff8e7;line-height:1.25;font-weight:800}
.roofscape{height:160px; position:relative; margin:0 auto 1.2rem; max-width:780px; border-bottom:4px solid var(--line); overflow:hidden;}
.roof{position:absolute; bottom:0; width:130px; height:76px; border:3px solid var(--line); background:var(--paper); transform:skewY(-2deg);}
.roof:before{content:''; position:absolute; left:18px; top:18px; width:28px; height:36px; border:3px solid var(--line); background:var(--accent-soft);}
.roof:after{content:''; position:absolute; right:17px; top:-34px; width:74px; height:46px; border-left:3px solid var(--line); border-top:3px solid var(--line); transform:skewY(-28deg) rotate(4deg);}
.roof.r1{left:5%;}.roof.r2{left:29%; height:105px; width:155px}.roof.r3{right:26%; height:88px}.roof.r4{right:3%; height:118px;width:145px}
.float-key{position:absolute; font-size:2rem; color:var(--accent); animation:float 2.8s ease-in-out infinite;}.k1{left:17%;top:13px}.k2{right:18%;top:38px;animation-delay:.8s}.k3{left:48%;top:2px;animation-delay:1.4s}
.scene-shell{max-width:900px; margin:0 auto; animation:scenein .42s cubic-bezier(.2,.8,.2,1);}
.journey-map{width:min(calc(100vw - 40px),calc((100svh - 40px)*1586/992));aspect-ratio:1586/992;border-radius:24px;border:1.5px solid #b8a58f;background-color:#9dd3ec;background-position:center;background-size:100% 100%;background-repeat:no-repeat;box-shadow:0 12px 34px rgba(91,74,57,.14);margin:0;left:50%;transform:translateX(-50%);position:relative;overflow:hidden}.journey-map:after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,transparent 60%,rgba(52,76,55,.12))}
.game-topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 10px;padding:9px 14px;border:1px solid #dbc5a2;border-radius:18px;background:rgba(255,248,225,.94);box-shadow:0 4px 14px rgba(94,78,65,.08)}.game-brand{font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif;font-size:1.4rem;font-weight:800;color:#7b5b34}.game-stats{display:flex;gap:8px;align-items:center}.game-stat{padding:5px 10px;border-radius:16px;background:#fff3cc;font-weight:700;font-size:.8rem}
.creator-shell{display:grid;grid-template-columns:.9fr 1.1fr;gap:22px;max-width:980px;margin:0 auto 70px}.creator-preview{border:1.5px solid #d8bc91;border-radius:24px;background:#fff5dc;padding:14px;box-shadow:0 10px 25px rgba(92,65,38,.12)}.creator-preview img{display:block;width:100%;max-height:54vh;object-fit:contain;border-radius:18px}.creator-controls{border:1.5px solid #e3cfad;border-radius:24px;background:#fffaf0;padding:20px}.creator-section{padding:11px 0;border-bottom:1px dashed #e1cba9}.creator-section:last-child{border-bottom:0}.creator-label{font-weight:800;margin-bottom:7px;color:#76583a}.accessory-badge{text-align:center;font-size:2rem;padding:8px;margin-top:8px;border-radius:16px;background:#fff0c9}
.st-key-avatar_preview{border:1.5px solid #d8bc91;border-radius:24px;background:#fff5dc;padding:14px;box-shadow:0 10px 25px rgba(92,65,38,.12)}.st-key-avatar_preview img{max-height:52vh;object-fit:contain;border-radius:18px}
.st-key-avatar_preview{position:relative}.st-key-avatar_preview .accessory-badge{position:absolute;right:22px;top:22px;z-index:3;min-width:82px;box-shadow:0 5px 14px rgba(92,65,38,.12)}
[data-testid="stForm"]{background:rgba(255,250,240,.94);border:1.5px solid #e0c8a2;border-radius:24px;padding:18px 20px;box-shadow:0 8px 24px rgba(94,68,38,.08)}
[data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]{background:#fff7e4!important;border-color:#d7bc91!important;border-radius:13px!important}
[data-testid="stSlider"] [role="slider"]{background:var(--accent)!important}.stRadio [role="radiogroup"]{gap:12px}.stRadio label{background:#fff5da;border:1px solid #dfc59d;border-radius:14px;padding:7px 11px}
[data-testid="stSlider"] [data-testid="stSliderTrackFill"]{background:var(--accent)!important}
[data-baseweb="radio"] input:checked~div{color:var(--accent)!important}
[data-baseweb="checkbox"] input:checked~div{background-color:var(--accent)!important;border-color:var(--accent)!important}
[data-baseweb="tag"]{background-color:var(--accent-soft)!important;color:var(--ink)!important}
.st-key-prior_experience_plain .stRadio label{background:transparent!important;border:0!important;border-radius:0!important;padding:3px 8px!important}
.day-route{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin:10px 0 16px}.day-node{width:48px;height:48px;border:2px solid #d1b687;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#fff5d8;font-weight:800;color:#9a7d57}.day-node.done{background:#88a557;color:white;border-color:#78964b}.day-node.now{background:#f5bd52;color:#65471f;border-color:#d89a35;transform:scale(1.12);box-shadow:0 0 0 5px rgba(245,189,82,.2)}
.day-summary{display:grid;grid-template-columns:.75fr 1.5fr .75fr;gap:16px;max-width:1000px;margin:10px auto 18px}.summary-card{border:1.5px solid #dec7a2;border-radius:20px;background:#fffaf0;padding:18px;box-shadow:0 7px 18px rgba(94,68,38,.08)}.summary-card h4{margin:0 0 12px}.summary-line{display:flex;justify-content:space-between;gap:8px;padding:9px 0;border-bottom:1px dashed #e5d3b6}.summary-line:last-child{border-bottom:0}.reward-number{font-size:2rem;color:var(--accent);font-weight:800;text-align:center}
.scene-number{text-align:center; color:var(--accent); font-size:.78rem; font-weight:700; letter-spacing:.18em; margin-bottom:.45rem;}
.scene-title{text-align:center;font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif;font-weight:800;font-size:clamp(2.15rem,5vw,3.5rem);margin:.05rem 0 .35rem;}
.scene-copy{text-align:center; color:var(--muted); font-size:.98rem; line-height:1.65; max-width:720px; margin:0 auto .8rem;}
.progress-dots{position:fixed;z-index:999;left:50%;bottom:14px;transform:translateX(-50%);display:flex;justify-content:center;gap:9px;margin:0;padding:9px 16px;background:rgba(251,250,246,.94);border:1px solid #d5cec5;border-radius:999px;box-shadow:0 4px 18px rgba(94,78,65,.12);backdrop-filter:blur(8px)}
.progress-dot{width:11px;height:11px;border:1.5px solid var(--line);border-radius:50%;background:transparent;transition:transform .25s ease,background .25s ease}.progress-dot.done{background:#b9ada2;border-color:#b9ada2}.progress-dot.now{background:var(--accent);border-color:var(--accent);transform:scale(1.28)}
.st-key-back_nav{position:fixed;left:18px;bottom:12px;z-index:1001;width:108px}.st-key-back_nav button{min-height:2.35rem!important;background:rgba(251,250,246,.96)!important;box-shadow:0 4px 14px rgba(94,78,65,.12)!important}
.st-key-cover_action{position:relative;z-index:5;width:min(390px,76vw);margin:-43vh auto 0;transform:translateY(-50%)}.st-key-cover_action button{min-height:4.65rem!important;border-radius:999px!important;font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif!important;font-size:clamp(1.7rem,2.6vw,2.25rem)!important;font-weight:800!important;letter-spacing:.08em!important;border-width:3px!important;box-shadow:0 7px 0 rgba(102,68,31,.3),0 12px 24px rgba(57,74,36,.18)!important}.st-key-cover_action button:hover{transform:translateY(-4px) scale(1.025)!important}.st-key-cover_action button[kind="primary"]{background:linear-gradient(180deg,#ffd986,#f3b94e)!important;color:#68451f!important;border-color:#f5e2a9!important}.st-key-cover_action button[kind="secondary"]{background:linear-gradient(180deg,#9eb35c,#7f9945)!important;color:#fffdf1!important;border-color:#d7e4a4!important}.st-key-cover_action [data-testid="stVerticalBlock"]{gap:1.15rem}.st-key-cover_settings{position:fixed;left:22px;top:20px;z-index:1002;width:120px}.st-key-cover_settings button{font-family:'Arial Rounded MT Bold','Noto Sans SC',sans-serif!important;font-size:1.15rem!important;font-weight:800!important;background:rgba(176,111,51,.9)!important;color:#fff8e7!important;border:2px solid #f3d29c!important}
.island-panel{border:1.5px solid #d6bd91;border-radius:24px;background:rgba(255,250,235,.94);padding:18px;box-shadow:0 9px 24px rgba(96,74,50,.12)}
.community-hero{height:clamp(190px,34vh,360px);border-radius:22px;background-size:cover;background-position:center;border:1.5px solid #cdb184;position:relative;overflow:hidden}.community-hero .label{position:absolute;left:18px;bottom:18px;background:rgba(255,248,226,.92);padding:10px 18px;border-radius:16px;font-weight:800;box-shadow:0 5px 15px rgba(70,55,35,.15)}
.detail-art{height:clamp(230px,43vh,470px);border-radius:24px;background-size:cover;background-position:center;border:1.5px solid #cdb184;box-shadow:0 10px 28px rgba(75,55,35,.13)}
.pros-cons{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}.pro,.con{padding:9px 11px;border-radius:12px;font-size:.8rem}.pro{background:#e7f0d4}.con{background:#fae0d1}
.bottom-nav{position:fixed;z-index:995;left:50%;bottom:12px;transform:translateX(-50%);display:flex;gap:5px;background:rgba(255,250,234,.96);border:1px solid #d1b586;border-radius:22px;padding:7px 9px;box-shadow:0 6px 24px rgba(76,58,35,.16);backdrop-filter:blur(9px)}.bottom-nav span{font-size:.72rem;padding:6px 10px;border-radius:14px;white-space:nowrap}.bottom-nav .active{background:#e9c36a;font-weight:800}
.st-key-bottom_nav_buttons{position:fixed;z-index:1000;left:50%;bottom:10px;transform:translateX(-50%);width:min(710px,88vw);background:rgba(255,250,234,.97);border:1px solid #d1b586;border-radius:20px;padding:5px 8px;box-shadow:0 6px 24px rgba(76,58,35,.16);backdrop-filter:blur(9px)}.st-key-bottom_nav_buttons button{min-height:2.25rem!important;font-size:.72rem!important;border:0!important;box-shadow:none!important;background:transparent!important;padding:4px!important}
.nest-room{height:clamp(280px,52vh,520px);border-radius:25px;background-size:cover;background-position:center;border:1.5px solid #c9aa78;box-shadow:0 12px 30px rgba(72,52,31,.14)}
.record-card{padding:13px 15px;border:1px solid #dec59e;border-radius:16px;background:#fffaf0;margin:8px 0}.setting-card{max-width:720px;margin:0 auto;padding:22px;border:1.5px solid #d7ba8a;border-radius:24px;background:#fffaf0}
.story-box{
  background:transparent; border:2px solid var(--line); border-radius:18px 15px 20px 14px;
  padding:12px 18px; color:var(--ink); font-size:.92rem; line-height:1.55; margin-bottom:10px;
}
.game-card{
  background:#fffefa; border:2px solid var(--line); border-radius:18px 15px 21px 14px;
  padding:13px 15px; min-height:292px; color:var(--ink); position:relative; transition:transform .2s ease,box-shadow .2s ease;
}
.room-art{height:138px;margin:-4px -5px 10px;border-radius:13px 11px 15px 10px;background-size:cover;background-position:center;border:1px solid #d7c8b7}
.game-card:hover{transform:translateY(-3px);box-shadow:6px 7px 0 var(--paper-2)}
.game-card.recommended{ border-color:var(--accent); box-shadow:5px 6px 0 var(--accent-soft); }
.game-card.locked{ opacity:.55; filter:grayscale(.4); }
.game-badge{
  display:inline-block; background:var(--accent-soft); color:#735719; font-size:.72rem; font-weight:700;
  padding:3px 9px; border-radius:20px; margin-bottom:6px;
}
.game-muted{ color:var(--muted); font-size:.85rem; }
.game-price{ font-size:1.7rem; font-weight:700; color:var(--accent); }
.landlord-tag{
  font-size:.72rem; color:var(--muted); display:flex; align-items:center; gap:5px; margin-bottom:6px;
}
.quest-row{ display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 14px; }
.quest-chip{
  font-size:.72rem; color:var(--muted); border:1px solid #aaa79f; padding:4px 10px; border-radius:20px;
}
.hud-row{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-bottom:15px}.hud-chip{border:1.5px solid var(--line);border-radius:20px;padding:5px 12px;font-size:.82rem;background:#fffefa}.hud-chip.coin{color:var(--accent)}.hud-chip.streak{color:var(--green)}
.badge-shelf{ display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.badge-pill{background:#fffefa;border:2px solid var(--line);border-radius:14px;padding:10px 14px;min-width:150px;text-align:center;animation:popin .3s ease}
.badge-pill .ic{ font-size:1.6rem; }
.badge-pill .t{font-weight:700;font-size:.85rem;margin-top:2px}.badge-pill .d{color:var(--muted);font-size:.72rem;margin-top:2px}
.avatar-caption{ text-align:center; font-size:.78rem; color:var(--mist); margin-top:2px; }
.dialogue-box{
  background:#fffefa; border:2px solid var(--line); border-radius:18px; padding:14px 18px;
  margin:8px 0 4px; animation: doorpop .35s cubic-bezier(.34,1.56,.64,1);
}
.dialogue-head{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.dialogue-portrait{width:38px;height:38px;border-radius:50%;background:var(--accent-soft);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}.dialogue-name{font-weight:700;color:var(--accent)}.dialogue-text{font-size:.9rem;line-height:1.7;color:var(--ink);min-height:44px}.dialogue-page{text-align:right;font-size:.72rem;color:var(--muted);margin-top:6px}
.clear-banner{
  text-align:center; padding:22px 10px; background:#fffefa;
  border:2px solid var(--line); border-radius:16px; margin-bottom:12px; animation: popin .4s ease;
}
.stButton>button{position:relative;overflow:hidden;border:1.5px solid var(--line);border-radius:18px 15px 20px 14px;font-weight:700;transition:transform .18s ease,box-shadow .18s ease,background .18s ease;min-height:2.65rem}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 6px 14px rgba(115,91,72,.16)!important}
.stButton>button:active{transform:translateY(1px) scale(.97);box-shadow:0 2px 5px rgba(115,91,72,.12)!important}
.stButton>button:after{content:'';position:absolute;inset:50%;border-radius:50%;background:rgba(255,255,255,.45);transform:scale(0);opacity:0;transition:transform .35s ease,opacity .45s ease}.stButton>button:active:after{inset:-35%;transform:scale(1);opacity:1;transition:0s}
button[kind="primary"]{background:var(--accent)!important;color:#5f4918!important;border-color:#d29a31!important;box-shadow:3px 4px 0 #e7cc8d!important}
button[kind="secondary"]{background:#fffefa!important;border-color:#b5a99d!important;color:var(--ink)!important}
.stProgress>div>div>div>div{background:var(--accent)}
.st-key-intro_page{min-height:calc(100svh - 5.5rem);display:flex;align-items:center}
.st-key-intro_page>[data-testid="stVerticalBlock"]{width:100%}
.st-key-intro_create_action{position:fixed;z-index:10;left:50%;top:50svh;transform:translate(-50%,-50%);width:min(520px,78vw)}
.st-key-intro_footer{position:fixed;z-index:10;left:50%;bottom:78px;transform:translateX(-50%);width:min(720px,calc(100vw - 40px))}
.st-key-intro_footer>[data-testid="stVerticalBlock"]{gap:.35rem}
.intro-note{text-align:center;color:var(--muted);font-size:.72rem;line-height:1.5;margin:12px auto 16px}
.option-sheet-tile{width:100%;aspect-ratio:1;box-sizing:border-box;border:2px solid transparent;border-radius:15px;background-repeat:no-repeat;overflow:hidden}
.option-sheet-tile.selected{border-color:var(--accent)}
.option-sheet-label{height:1.4rem;display:flex;align-items:center;justify-content:center;text-align:center;white-space:nowrap;font-size:.72rem;font-weight:700;margin:5px 0 6px;color:var(--ink)}
.scene-copy:empty{display:none}
.stApp:has(.st-key-character_creator) .block-container{max-width:1240px}
.stApp:has(.st-key-character_creator) .scene-title{font-size:clamp(2rem,3.2vw,3rem);margin-bottom:.75rem}
.stApp:has(.st-key-character_creator) .scene-number{font-size:.72rem;margin-bottom:.25rem}
.st-key-character_creator>[data-testid="stVerticalBlock"]{gap:0}
.st-key-character_creator>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]{align-items:stretch;gap:2rem}
.st-key-character_creator>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{display:flex;align-self:stretch}
.st-key-character_creator>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]>[data-testid="stVerticalBlock"]{width:100%;height:100%}
.st-key-character_creator>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:first-child{position:relative;min-height:100%}
.st-key-character_creator .st-key-avatar_preview{position:absolute;inset:0;height:100%;min-height:100%;box-sizing:border-box;display:flex;align-items:flex-start;justify-content:center;padding:28px 22px}
.st-key-character_creator .st-key-avatar_preview>[data-testid="stVerticalBlock"]{width:100%;height:100%;display:flex;justify-content:flex-start}
.st-key-character_creator .st-key-avatar_preview [data-testid="stImage"]{width:100%}
.st-key-character_creator .st-key-avatar_preview img{width:100%;max-height:54vh;object-fit:contain}
.st-key-character_creator>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"]{display:flex!important;flex-wrap:nowrap!important;gap:1rem!important}
.st-key-character_creator>[data-testid="stLayoutWrapper"]>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:nth-child(2) [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{flex:1 1 0!important;width:0!important;min-width:0!important}
@media(min-width:701px) and (max-height:900px){
  .stApp:has(.st-key-character_creator) .block-container{padding-top:.45rem;padding-bottom:1rem}
  .st-key-character_creator{zoom:.80;width:125%;margin-left:0}
  .st-key-creator_submit{position:relative;margin-top:1.25rem;margin-bottom:3.75rem;z-index:2}
}
button,button:hover,button:active,button:focus,
[data-testid="stButton"],[data-testid="stFormSubmitButton"],[data-testid^="baseButton-"]{
  box-shadow:none!important;filter:none!important;text-shadow:none!important;
}
@media(min-width:900px) and (max-height:820px){.block-container{padding-top:.55rem}.roofscape{height:112px;margin-bottom:.4rem}.narrative-stage{min-height:57vh}.island-cover{min-height:68vh}.cover-copy{padding:18px 38px}.narrative-title{font-size:5.4rem}.scene-title{font-size:2.55rem}.scene-copy{margin-bottom:.45rem}.room-art{height:105px}.game-card{min-height:260px;padding:10px 13px}.game-card p{margin:.3rem 0!important;line-height:1.45!important}.hud-row{margin-bottom:7px}.story-box{padding:9px 14px}}
@media(max-width:700px){.block-container{padding-top:.45rem}.island-cover{height:calc(100vh - .9rem);min-height:600px;border-radius:20px;background-position:center}.cover-copy{margin-top:12vh;width:96%}.narrative-title{font-size:clamp(3.6rem,18vw,5.2rem)}.narrative-subtitle{margin-top:16px;padding:8px 24px 10px;font-size:1.45rem}.st-key-cover_action{width:min(340px,78vw);margin:-39vh auto 0}.st-key-cover_action button{min-height:4.1rem!important;font-size:1.65rem!important}.st-key-cover_settings{left:12px;top:12px;width:98px}.narrative-stage{min-height:72vh}.roofscape{height:120px}.game-card{min-height:0}.progress-dots{bottom:8px}.creator-shell,.day-summary{grid-template-columns:1fr}.creator-preview img{max-height:45vh}.game-topbar{align-items:flex-start}.game-stats{flex-wrap:wrap;justify-content:flex-end}.day-summary{margin-bottom:80px}}
@keyframes fadein{ from{opacity:0; transform:translateY(4px);} to{opacity:1; transform:translateY(0);} }
@keyframes popin{ from{opacity:0; transform:scale(.85);} to{opacity:1; transform:scale(1);} }
@keyframes doorpop{ from{opacity:0; transform:scale(.9) translateY(6px);} to{opacity:1; transform:scale(1) translateY(0);} }
@keyframes float{0%,100%{transform:translateY(0) rotate(-5deg)}50%{transform:translateY(-9px) rotate(5deg)}}
@keyframes scenein{from{opacity:0;transform:translateY(16px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes coverReveal{from{opacity:0;transform:scale(1.015)}to{opacity:1;transform:scale(1)}}
@keyframes oceanBreath{0%,100%{background-size:cover;background-position:50% 50%}50%{background-size:auto 104%;background-position:50% 51%}}
@keyframes titleFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes sunGlow{0%,100%{opacity:.55;transform:scale(1)}50%{opacity:.95;transform:scale(1.04)}}
@keyframes twinkle{0%,100%{opacity:.35;transform:scale(.75) rotate(0)}50%{opacity:1;transform:scale(1.2) rotate(18deg)}}
/* 2026-07 cover and housing-flow refinements */
.island-cover{width:100vw;height:100svh;min-height:640px;aspect-ratio:auto;margin-left:calc(50% - 50vw);border-radius:0;background-size:cover;background-position:center center;animation:coverReveal .7s ease-out both}
.cover-copy{width:min(580px,50vw);margin-top:3vh;background:transparent}.cover-title-art{display:block;width:100%;height:auto;margin:0 auto;mix-blend-mode:normal;filter:drop-shadow(0 7px 8px rgba(93,65,30,.12));animation:titleFloat 4.8s ease-in-out infinite}
.st-key-cover_action{margin:-38svh auto 0;transform:none}
.game-topbar{height:58px;margin:0 0 12px;padding:0;border:0;background:transparent;box-shadow:none}
.game-location{position:fixed;z-index:990;left:20px;top:16px;padding:8px 14px;border:1px solid #dbc5a2;border-radius:15px;background:rgba(255,248,225,.94);box-shadow:0 4px 14px rgba(94,78,65,.08);font-size:.82rem;line-height:1.35}.game-location b{font-size:1rem}
.game-stats{position:fixed;z-index:990;right:20px;top:16px;display:flex;gap:7px;align-items:center}.game-stat{padding:7px 11px;border:1px solid #e1c99d;border-radius:16px;background:rgba(255,243,204,.94);font-size:.78rem;box-shadow:0 4px 12px rgba(94,78,65,.07)}
.game-brand{position:fixed;z-index:989;right:22px;bottom:18px;font-size:.92rem;background:rgba(255,248,225,.92);border:1px solid #d8bc8c;border-radius:14px;padding:7px 11px;box-shadow:0 4px 12px rgba(94,78,65,.1)}
.game-card{padding:18px;min-height:270px}.game-card h4{font-size:1rem!important;line-height:1.45}
.property-detail-shell{display:grid;grid-template-columns:1.05fr .95fr;gap:24px;padding:22px;border:1.5px solid #dec8a4;border-radius:25px;background:#fff8e9;box-shadow:0 10px 28px rgba(75,55,35,.1)}
.property-detail-shell .detail-art{height:auto;min-height:390px;border-radius:20px;box-shadow:none}.property-copy{padding:4px 5px}.property-copy h2{font-size:1.55rem;margin:6px 0 3px}.property-meta{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin:16px 0}.property-meta span{padding:8px 10px;border-radius:11px;background:#f7edd7;font-size:.82rem}.property-review{border-top:1px dashed #d7be96;margin-top:14px;padding-top:12px;line-height:1.75}
@media(max-width:700px){.island-cover{width:100vw;height:100svh;min-height:600px;aspect-ratio:auto;background-size:cover;background-position:center center}.cover-copy{width:74vw;margin-top:5vh}.cover-title-art{width:100%;margin:0 auto}.st-key-cover_action{margin:-39svh auto 0;transform:none}.game-location{position:relative;left:auto;top:auto;display:inline-block}.game-stats{position:relative;right:auto;top:auto;justify-content:flex-end}.game-brand{right:12px;bottom:72px}.property-detail-shell{grid-template-columns:1fr;padding:14px}.property-detail-shell .detail-art{min-height:260px}}
/* The cover is a true single-screen scene: no Streamlit gutters or overflow. */
.stApp:has(.island-cover),
.stAppViewContainer:has(.island-cover),
[data-testid="stAppViewContainer"]:has(.island-cover),
[data-testid="stMain"]:has(.island-cover){height:100svh!important;min-height:100svh!important;overflow:hidden!important}
.stApp:has(.island-cover) .block-container{width:100%!important;max-width:none!important;height:100svh!important;padding:0!important;margin:0!important;overflow:hidden!important}
.island-cover{position:fixed!important;inset:0!important;width:100vw!important;height:100dvh!important;min-height:0!important;margin:0!important;border-radius:0!important;background-color:#55b7d4!important;background-size:cover!important;background-position:center center!important;background-repeat:no-repeat!important}
.stApp:has(.island-cover) .st-key-cover_action{position:fixed;z-index:1003;left:50%;top:66svh;width:min(390px,76vw);margin:0;transform:translateX(-50%)}
.stApp:has(.island-cover) .st-key-cover_settings{position:fixed}
.st-key-cover_action button,.st-key-cover_action button p{font-size:clamp(1.55rem,2.25vw,2rem)!important;font-weight:600!important;line-height:1.15!important}
html,body,#root{margin:0!important;padding:0!important}
@media(max-width:700px){.stApp:has(.island-cover) .st-key-cover_action{top:64svh;width:min(340px,78vw);margin:0;transform:translateX(-50%)}.stApp:has(.island-cover) .cover-copy{margin-top:3vh}}
.cover-copy{z-index:2}
.journey-selection-map{position:relative;left:50%;transform:translateX(-50%);width:min(calc(100vw - 40px),calc((100svh - 40px)*1586/992));aspect-ratio:1586/992;margin:0 0 72px;border-radius:24px;background-color:#9dd3ec;background-position:center;background-size:100% 100%;background-repeat:no-repeat;box-shadow:0 14px 36px rgba(62,85,74,.18);overflow:hidden}.journey-day-link{position:absolute;display:block;width:10%;height:8%;border-radius:14px;transform:translate(-50%,-50%);transition:filter .2s ease,transform .2s ease}.journey-day-link.active{z-index:3;border:3px solid #fff6b8;background:rgba(255,223,105,.16);box-shadow:0 0 0 6px rgba(255,226,111,.28),0 0 28px rgba(255,245,167,.9);animation:mapPulse 1.8s ease-in-out infinite;cursor:pointer}.journey-day-link.active:hover{transform:translate(-50%,-50%) scale(1.06)}.journey-day-link.locked{z-index:2;background:rgba(66,72,63,.48);border:2px solid rgba(75,70,60,.28);cursor:not-allowed}.journey-day-link.done{z-index:2;background:rgba(255,250,216,.08);border:2px solid rgba(255,255,235,.5)}.journey-day-link.d1{left:32%;top:31%}.journey-day-link.d2{left:68%;top:31%}.journey-day-link.d3{left:51%;top:48%}.journey-day-link.d4{left:29%;top:61%}.journey-day-link.d5{left:44%;top:79%}.journey-day-link.d6{left:75%;top:64%}@keyframes mapPulse{0%,100%{filter:brightness(1)}50%{filter:brightness(1.16)}}
@media(max-width:700px){.journey-map,.journey-selection-map{width:min(98vw,calc((100svh - 80px)*1586/992));border-radius:12px}.journey-day-link{width:12%;height:10%;border-radius:8px}.journey-day-link.active{border-width:2px;box-shadow:0 0 0 3px rgba(255,226,111,.3),0 0 16px rgba(255,245,167,.8)}}
.journey-day-link.locked,.journey-day-link.done{pointer-events:none}
</style>
"""

ROUND_STORY = {
    1: ("海湾社区", "靠近海边与渔港，咖啡香和慢节奏一起吹来。"),
    2: ("绿野社区", "植物丰盛而安静，适合想亲近自然的住民。"),
    3: ("岛中央城区", "商店集中、交通方便，也拥有更热闹的人流。"),
    4: ("旧街社区", "老建筑与熟悉的邻里，让生活成本更从容。"),
    5: ("湖畔新区", "新设施与湖景并存，是整洁舒适的新生活。"),
    6: ("晨光社区", "海风、晨光和码头新居交织成旅程的最后一站。"),
}

COMMUNITY_ASSETS = {
    1:"community-bay-v2.jpg",2:"community-green-v2.jpg",3:"community-city-v2.jpg",
    4:"community-oldstreet-v2.jpg",5:"community-lake-v2.jpg",6:"community-free-v2.jpg",
}

# --------------------------------------------------------------------------
# Street geometry — shared constants so app.py and game_ui.py agree on
# where doors/coins sit without duplicating magic numbers.
# --------------------------------------------------------------------------

STREET_WIDTH = 820
DOOR_X = {"A": 140, "B": 400, "C": 660}
COIN_X = [55, 270, 530, 760]
MOVE_STEP = 55
RUN_STEP = 130
KNOCK_RANGE = 60
COIN_RANGE = 28

AVATARS = [
    {"id": "scout", "emoji": "🧑‍🎒", "name": "背包客", "desc": "轻装上阵，什么都想去看看", "color": "#FF6B5C", "cap": "#7a1f14"},
    {"id": "planner", "emoji": "🧑‍💻", "name": "精算派", "desc": "每一分钱都要花在刀刃上", "color": "#6FCF97", "cap": "#2f6d4e"},
    {"id": "night", "emoji": "🧑‍🚀", "name": "夜归人", "desc": "通勤和安全感是第一位的", "color": "#B7A9E0", "cap": "#4a3b78"},
    {"id": "social", "emoji": "🧑‍🎨", "name": "生活家", "desc": "在意社区氛围和装修质感", "color": "#FFD166", "cap": "#8a6a1f"},
]

LANDLORDS = [
    {"emoji": "🧔", "name": "老张", "line": "这套我自己都想住，采光是真的好。"},
    {"emoji": "👩‍🦳", "name": "王阿姨", "line": "小伙子/小姑娘看着就靠谱，价格还能聊。"},
    {"emoji": "🧑‍💼", "name": "中介小李", "line": "这套挂出来没两天，手慢无哦。"},
    {"emoji": "👨‍🔧", "name": "房东老周", "line": "楼下就是菜市场，生活方便得很。"},
    {"emoji": "👵", "name": "刘婆婆", "line": "我在这住了十几年，邻里都熟。"},
    {"emoji": "🧑‍🚀", "name": "合租室友阿飞", "line": "我们几个都挺好相处，随时来看房。"},
    {"emoji": "👨‍💼", "name": "地产顾问陈生", "line": "地铁口就在旁边，通勤能省不少时间。"},
    {"emoji": "🧑‍🎨", "name": "二房东小美", "line": "刚重新装修过，家具家电都是新的。"},
]


def landlord_for(round_number: int, label: str) -> dict:
    idx = (round_number * 3 + (ord(label) - ord("A"))) % len(LANDLORDS)
    return LANDLORDS[idx]


def _avatar(avatar_id: Optional[str]) -> dict:
    return next((a for a in AVATARS if a["id"] == avatar_id), AVATARS[0])


# --------------------------------------------------------------------------
# Basic chrome
# --------------------------------------------------------------------------

def inject_game_css() -> None:
    st.markdown(GAME_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _asset_data_url(path: str) -> str:
    data = Path(path).read_bytes()
    mime = "image/jpeg" if Path(path).suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def title_scene() -> None:
    """Render the opening cover with one responsive background image."""
    cover = _asset_data_url("assets/image2/rent-island-cover-v2.png")
    title_art = _asset_data_url("assets/image2/rent-island-title-transparent-v1.png")
    settings_art = _asset_data_url("assets/image2/settings-sign-transparent-v1.png")
    st.markdown(
        f"""
        <style>
        .st-key-cover_settings{{left:14px!important;top:0!important;width:112px!important;}}
        .st-key-cover_settings button{{width:112px!important;height:69px!important;min-height:69px!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent url('{settings_art}') center/contain no-repeat!important;box-shadow:none!important;color:transparent!important;}}
        .st-key-cover_settings button p{{color:transparent!important;font-size:0!important;}}
        .st-key-cover_settings button:hover{{transform:translateY(3px) scale(1.03)!important;box-shadow:none!important;}}
        @media(max-width:700px){{.st-key-cover_settings{{left:6px!important;width:92px!important}}.st-key-cover_settings button{{width:92px!important;height:57px!important;min-height:57px!important}}}}
        </style>
        <div class="island-cover" style="background-image:url('{cover}')">
          <div class="cover-copy">
            <img class="cover-title-art" src="{title_art}" alt="租房小岛，找到你理想的小窝">
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def journey_map() -> None:
    artwork = _asset_data_url("assets/image2/rental-journey-map-user.png")
    st.markdown(
        f"<div class='journey-map' role='img' aria-label='六个租房社区组成的小岛地图' style=\"background-image:url('{artwork}')\"></div>",
        unsafe_allow_html=True,
    )


def interactive_journey_map(active_day: int) -> None:
    """Clickable six-day island map; only the current day is enabled."""
    artwork = _asset_data_url("assets/image2/rental-journey-map-user.png")
    links = []
    for day in range(1, 7):
        state = "active" if day == active_day else "done" if day < active_day else "locked"
        participant = st.session_state.get("participant_id", "")
        href = f"?participant={participant}&map_day={day}" if day == active_day else "#"
        label = ROUND_STORY[day][0]
        links.append(
            f'<a class="journey-day-link d{day} {state}" href="{href}" target="_self" '
            f'aria-label="第 {day} 天 {label}" title="第 {day} 天 · {label}"></a>'
        )
    st.markdown(
        f'<div class="journey-selection-map" role="img" aria-label="我的租房之旅" '
        f'style="background-image:url(\'{artwork}\')">{"".join(links)}</div>',
        unsafe_allow_html=True,
    )


def community_hero(day: int, title: str, description: str) -> None:
    art = _asset_data_url(f"assets/image2/{COMMUNITY_ASSETS.get(day, COMMUNITY_ASSETS[1])}")
    st.markdown(
        f"<div class='community-hero' style=\"background-image:url('{art}')\"><div class='label'>第 {day} 天 · {title}<br><small>{description}</small></div></div>",
        unsafe_allow_html=True,
    )


def bottom_nav(active: str = "map") -> None:
    items = [("map","🏝 小岛地图"),("nest","🏠 我的小窝"),("records","🔍 看房记录"),("favorites","⭐ 收藏"),("settings","⚙ 设置")]
    html = "".join(f"<span class='{'active' if key == active else ''}'>{label}</span>" for key, label in items)
    st.markdown(f"<div class='bottom-nav'>{html}</div>", unsafe_allow_html=True)


def nest_room(theme: str) -> None:
    filename = {"ocean":"nest-ocean-v2.jpg", "green":"nest-green-v2.jpg", "journal":"nest-journal-v2.jpg"}.get(theme, "nest-ocean-v2.jpg")
    art = _asset_data_url(f"assets/image2/{filename}")
    st.markdown(f"<div class='nest-room' style=\"background-image:url('{art}')\"></div>", unsafe_allow_html=True)


HAIR_OPTIONS = {"short": "齐肩短发", "long": "侧分中长发", "twin": "双丸子头", "curly": "自然长卷发"}
HAIR_COLOR_OPTIONS = {"black":"黑色", "brown":"棕色", "blonde":"金色"}
OUTFIT_OPTIONS = {"tee": "绿色背带裤", "hoodie": "绿色背带裙", "shirt": "粉色连衣裙", "jacket": "黄色外套"}
BOTTOM_OPTIONS = {"jeans":"牛仔裤", "shorts":"短裤", "skirt":"长裙"}
ACCESSORY_OPTIONS = {"bag": ("👜", "随身小包"), "cap": ("🧢", "遮阳帽"), "glasses": ("👓", "圆框眼镜"), "headphones": ("🎧", "通勤耳机")}


AVATAR_HAIR_FILES = {
    "short": "bangs",
    "long": "bob",
    "twin": "buns",
    "curly": "long",
}
AVATAR_OUTFIT_FILES = {
    "tee": "shorts",
    "hoodie": "dress",
    "shirt": "pink",
    "jacket": "yellow",
}


def avatar_asset(hair: str, outfit: str = "tee") -> str:
    """Return the aligned full-body preview for one hair/outfit pairing."""
    safe_hair = AVATAR_HAIR_FILES.get(hair, "bangs")
    safe_outfit = AVATAR_OUTFIT_FILES.get(outfit, "shorts")
    return f"assets/avatar_female/preview/{safe_hair}_{safe_outfit}.png"


def _option_sheet_tile(
    sheet_path: str,
    index: int,
    label: str,
    selected: bool,
    zoom: float = 1.0,
    position_offset: tuple[float, float] = (0.0, 0.0),
) -> None:
    """Render one quadrant from a 2x2 user-provided option sheet."""
    artwork = _asset_data_url(sheet_path)
    # Zoom each quadrant around its own center, so differently shaped artwork
    # has one consistent perceived size without drifting out of alignment.
    if zoom == 1:
        near, far = 0.0, 100.0
    else:
        near = 50 * (1 - zoom) / (1 - 2 * zoom)
        far = 100 - near
    x = (near if index % 2 == 0 else far) + position_offset[0]
    y = (near if index < 2 else far) + position_offset[1]
    state = " selected" if selected else ""
    st.markdown(
        f"<div class='option-sheet-tile{state}' style=\"background-image:url('{artwork}');background-size:{200 * zoom:.2f}% {200 * zoom:.2f}%;background-position:{x:.2f}% {y:.2f}%\" role='img' aria-label='{label}'></div><div class='option-sheet-label'>{label}</div>",
        unsafe_allow_html=True,
    )


def character_creator() -> dict:
    """Full character setup. Visual variants are real image2 assets."""
    st.session_state.setdefault("avatar_hair", "short")
    st.session_state.setdefault("avatar_hair_color", "brown")
    st.session_state.setdefault("avatar_outfit", "tee")
    st.session_state.setdefault("avatar_bottom", "shorts")
    st.session_state.setdefault("avatar_accessory", "bag")
    st.session_state.setdefault("player_name", "小岛新住民")
    with st.container(key="character_creator"):
        preview, controls = st.columns([.82, 1.18], gap="large")
        with preview:
            with st.container(key="avatar_preview"):
                st.image(
                    avatar_asset(st.session_state.avatar_hair, st.session_state.avatar_outfit),
                    use_container_width=True,
                )
        with controls:
            st.markdown("#### 创建你的角色")
            st.session_state.player_name = st.text_input("起个名字", value=st.session_state.player_name, max_chars=16)
            st.markdown("<div class='creator-label'>选择发型</div>", unsafe_allow_html=True)
            hair_cols = st.columns(4)
            hair_zoom = [1.0, 1.04, 1.12, 1.02]
            hair_offsets = [(0, 0), (-2.5, 0), (0, -5.0), (2.5, 0)]
            for index, (col, (key, label)) in enumerate(zip(hair_cols, HAIR_OPTIONS.items())):
                with col:
                    _option_sheet_tile("assets/image2/hair-options-sheet-v2.png", index, label, st.session_state.avatar_hair == key, hair_zoom[index], hair_offsets[index])
                    if st.button("已选择" if st.session_state.avatar_hair == key else "选择", key=f"hair_{key}", type="primary" if st.session_state.avatar_hair == key else "secondary", use_container_width=True):
                        st.session_state.avatar_hair = key
                        st.rerun()
            st.markdown("<div class='creator-label'>选择服装</div>", unsafe_allow_html=True)
            outfit_cols = st.columns(4)
            outfit_zoom = [1.04, 1.0, 1.05, 1.0]
            for index, (col, (key, label)) in enumerate(zip(outfit_cols, OUTFIT_OPTIONS.items())):
                with col:
                    _option_sheet_tile("assets/image2/outfit-options-sheet-v2.png", index, label, st.session_state.avatar_outfit == key, outfit_zoom[index])
                    if st.button("已选择" if st.session_state.avatar_outfit == key else "选择", key=f"outfit_{key}", type="primary" if st.session_state.avatar_outfit == key else "secondary", use_container_width=True):
                        st.session_state.avatar_outfit = key
                        st.rerun()
    return {
        "hair": st.session_state.avatar_hair,
        "hair_color": st.session_state.avatar_hair_color,
        "outfit": st.session_state.avatar_outfit,
        "bottom": st.session_state.avatar_bottom,
        "accessory": st.session_state.avatar_accessory,
        "name": st.session_state.player_name,
    }


def game_topbar(day: int, total_days: int, coins: int, player_name: str, accessory: str) -> None:
    community = ROUND_STORY.get(day, (f"第 {day} 天", ""))[0]
    st.markdown(
        f"""<div class='game-topbar'><div class='game-location'><b>{community}</b><br>第 {day}/{total_days} 天</div>
        <div class='game-stats'><span class='game-stat'>🪙 {coins}</span><span class='game-stat'>🏅 {len(st.session_state.get('badges_earned', []))}</span><span class='game-stat'>👤 {player_name}</span></div>
        <div class='game-brand'>🏝️ 租房小岛</div></div>""",
        unsafe_allow_html=True,
    )


def day_route(day: int, total_days: int) -> None:
    nodes = "".join(
        f"<span class='day-node {'done' if i < day else 'now' if i == day else ''}'>{'✓' if i < day else i}</span>"
        for i in range(1, total_days + 1)
    )
    st.markdown(f"<div class='day-route'>{nodes}</div>", unsafe_allow_html=True)


def day_summary_card(round_number: int, row: dict, coins_earned: int) -> None:
    satisfaction = int(row.get("satisfaction", 0))
    confidence = int(row.get("choice_confidence", 0))
    followed = bool(row.get("recommendation_followed"))
    st.markdown(
        f"""<div class='day-summary'>
        <div class='summary-card'><h4>🏡 今日落脚</h4><b>房源 {row.get('chosen_listing_id','')}</b><p class='game-muted'>月租 ¥{int(row.get('chosen_rent',0)):,}<br>面积 {float(row.get('chosen_area',0)):.0f}㎡</p></div>
        <div class='summary-card'><h4>第 {round_number} 天评价</h4>
          <div class='summary-line'><span>满意程度</span><b>{'♥' * min(5, max(1, round(satisfaction / 1.4)))}</b></div>
          <div class='summary-line'><span>选择信心</span><b>{confidence}/7</b></div>
          <div class='summary-line'><span>偏好匹配</span><b>{'跟随推荐' if followed else '自主选择'}</b></div>
        </div>
        <div class='summary-card'><h4>🎁 今日收获</h4><div class='reward-number'>+{coins_earned}</div><p style='text-align:center'>岛屿币</p></div>
        </div>""",
        unsafe_allow_html=True,
    )


def character_identity_card(hair: str, outfit: str, accessory: str, name: str, coins: int, badges: list[dict], group_label: str, hair_color: str = "brown") -> None:
    left, right = st.columns([.35, .65])
    with left:
        st.image(avatar_asset(hair, outfit), use_container_width=True)
    with right:
        icon, accessory_name = ACCESSORY_OPTIONS.get(accessory, ("👜", "随身小包"))
        st.markdown(f"### {icon} {name}")
        st.write(f"体验模式：{group_label}")
        st.write(f"配饰：{accessory_name} · 累计岛屿币：🪙 {coins} · 成就：🏅 {len(badges)}")


def scene_heading(number: str, title: str, copy: str) -> None:
    st.markdown(
        f"""<div class="scene-shell">
          <div class="scene-number">{number}</div>
          <div class="scene-title">{title}</div>
          <div class="scene-copy">{copy}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def progress_dots(current: int, total: int) -> None:
    dots = "".join(
        f"<span class='progress-dot {'done' if i < current else 'now' if i == current else ''}'></span>"
        for i in range(total)
    )
    st.markdown(f"<div class='progress-dots'>{dots}</div>", unsafe_allow_html=True)


def quest_log(steps: list[str], current: int) -> None:
    chips = ""
    for i, step in enumerate(steps):
        state = "done" if i < current else ("now" if i == current else "")
        opacity = "1" if state in ("done", "now") else ".5"
        border = "var(--accent)" if state == "now" else "#aaa79f"
        chips += f"<span class='quest-chip' style='opacity:{opacity};border-color:{border};'>{step}</span>"
    st.markdown(f"<div class='quest-row'>{chips}</div>", unsafe_allow_html=True)


def hud_bar(coins: int, streak: int, badges_count: int) -> None:
    st.markdown(
        f"""<div class='hud-row'>
          <span class='hud-chip coin'>🪙 {coins} 积分</span>
          <span class='hud-chip streak'>🔥 连续满意 {streak}</span>
          <span class='hud-chip'>🏅 成就 {badges_count}</span>
        </div>""",
        unsafe_allow_html=True,
    )


def intro_skyline(height: int = 150) -> None:
    heights = [40, 70, 55, 95, 60, 80, 45, 60]
    bldgs = ""
    for h in heights:
        wins = ""
        for r in range(max(1, h // 20)):
            for c in range(2):
                lit = "background:#FFD166;box-shadow:0 0 6px 1px rgba(255,209,102,.6);" if (r + c) % 2 == 0 else "background:rgba(255,255,255,.08);"
                wins += f"<div style='position:absolute;width:5px;height:5px;border-radius:1px;left:{6+c*14}px;bottom:{8+r*16}px;{lit}'></div>"
        bldgs += f"<div style='position:relative;flex:1;height:{h}px;background:linear-gradient(180deg,#4a3b78,#241a40);border-radius:3px 3px 0 0;'>{wins}</div>"
    html = f"""
    <div style="height:{height}px;border-radius:14px;overflow:hidden;border:2px solid #4a3b78;
      background:linear-gradient(180deg,#241645 0%, #ff8a5b 100%); display:flex; align-items:flex-end; gap:6px; padding:0 8px;">
      {bldgs}
    </div>
    """
    components.html(html, height=height + 10)


def avatar_picker(key: str = "avatar") -> str:
    if key not in st.session_state:
        st.session_state[key] = AVATARS[0]["id"]
    st.markdown("<div class='game-muted' style='margin-bottom:6px;'>先选一个探索者形象（会出现在街景里，仅用于装饰不会被记录）：</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, av in enumerate(AVATARS):
        active = st.session_state[key] == av["id"]
        with cols[i]:
            if st.button(av["emoji"], key=f"{key}_btn_{av['id']}", type="primary" if active else "secondary", use_container_width=True):
                st.session_state[key] = av["id"]
                st.rerun()
            st.markdown(f"<div class='avatar-caption'><b>{av['name']}</b><br>{av['desc']}</div>", unsafe_allow_html=True)
    return st.session_state[key]


# --------------------------------------------------------------------------
# Interactive street — real left/right movement via Streamlit buttons,
# door proximity, coin pickups, NPC standees with proximity speech bubbles.
# --------------------------------------------------------------------------

_SKY_STAGES = [
    ("#274690 0%, #ff9a5b 100%", "☀️", 0),
    ("#243b6b 0%, #ff8a5b 100%", "🌤️", 3),
    ("#241645 0%, #ff7a5b 100%", "🌇", 6),
    ("#1c1240 0%, #6b4a8a 100%", "🌆", 12),
    ("#120b2c 0%, #3a2a63 100%", "🌃", 20),
    ("#0a0620 0%, #241645 100%", "🌌", 30),
]


def interactive_street(
    round_number: int,
    total_rounds: int,
    x: int,
    avatar: Optional[str],
    doors: dict,
    landlords: dict,
    collected_coins: set,
    facing: str = "right",
    height: int = 230,
) -> None:
    """Renders the walkable street. `x` is the character's real position
    (from st.session_state.street_x, moved by ◀/▶ buttons in app.py).
    Purely a renderer — takes plain data, writes nothing.
    """
    idx = min(round_number - 1, len(_SKY_STAGES) - 1)
    gradient, sky_icon, n_stars = _SKY_STAGES[idx]
    av = _avatar(avatar)
    flip = "scaleX(-1)" if facing == "left" else "scaleX(1)"

    stars_html = "".join(
        f"<div class='star' style='left:{7+i*17%94}%; top:{6+(i*13)%50}%; animation-delay:{i*0.35}s;'></div>"
        for i in range(n_stars)
    )

    doors_html = ""
    for label, dx in doors.items():
        near = abs(x - dx) <= KNOCK_RANGE
        ll = landlords[label]
        bubble = f"<div class='street-bubble'>👋 过来看看 {label} 号房！</div>" if near else ""
        ring = "door-near" if near else ""
        doors_html += f"""
        <div class="door-wrap {ring}" style="left:{dx}px;">
          <div class="street-npc">{ll['emoji']}</div>
          {bubble}
          <div class="door-frame">
            <div class="door-label">{label}</div>
          </div>
        </div>
        """

    coins_html = ""
    for i, cx in enumerate(COIN_X):
        if i in collected_coins:
            continue
        coins_html += f"<div class='coin' style='left:{cx}px;'>🪙</div>"

    html = f"""
    <style>
      .street{{position:relative;height:{height}px;border-radius:14px;overflow:hidden;border:2px solid #4a3b78;
        background:linear-gradient(180deg,{gradient}); transition:background 1s ease;}}
      .star{{position:absolute;width:2px;height:2px;background:#fff;border-radius:50%;opacity:.2;animation:twinkle 2.4s ease-in-out infinite;}}
      @keyframes twinkle{{0%,100%{{opacity:.15;}}50%{{opacity:.9;}}}}
      .ground{{position:absolute;left:0;right:0;bottom:0;height:40px;
        background:repeating-linear-gradient(90deg,#3a2c63 0 24px,#342456 24px 48px); border-top:3px solid #6fcf9770;}}
      .track{{position:absolute; left:0; right:0; bottom:40px; height:150px;}}
      .door-wrap{{position:absolute; bottom:0; width:60px; text-align:center; transition:filter .3s ease;}}
      .door-wrap.door-near .door-frame{{box-shadow:0 0 0 3px #FFD166, 0 0 16px rgba(255,209,102,.6);}}
      .door-frame{{width:44px;height:70px;margin:0 auto; background:linear-gradient(180deg,#4a3b78,#342456);
        border:2px solid #5b4a8a; border-radius:6px 6px 0 0; display:flex; align-items:flex-end; justify-content:center;}}
      .door-label{{font-family:'Press Start 2P',monospace; font-size:.6rem; color:var(--amber); margin-bottom:6px;}}
      .street-npc{{font-size:22px; animation:bob 1.4s ease-in-out infinite;}}
      .street-bubble{{position:absolute; top:-30px; left:50%; transform:translateX(-50%); white-space:nowrap;
        background:rgba(0,0,0,.55); color:#fff; font-size:.66rem; padding:3px 8px; border-radius:10px; animation:fadein .25s ease;}}
      .coin{{position:absolute; bottom:44px; font-size:18px; animation:coinspin 1.1s linear infinite, bob 1s ease-in-out infinite;}}
      @keyframes coinspin{{0%{{transform:rotateY(0);}}100%{{transform:rotateY(360deg);}}}}
      @keyframes bob{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(-4px);}}}}
      .char{{position:absolute; bottom:40px; width:26px; height:38px; transition:left .25s ease; transform:{flip};}}
      .char .head{{width:15px;height:15px;background:#FFE0B5;border-radius:50%;margin:0 auto;border:2px solid #3a2205; position:relative;}}
      .char .cap{{position:absolute; top:-7px; left:-2px; width:19px; height:9px; background:{av['cap']}; border-radius:10px 10px 0 0;}}
      .char .body{{width:20px;height:16px;background:{av['color']};border-radius:4px;margin:-2px auto 0;border:2px solid #3a2205;}}
      .char .legs{{display:flex; justify-content:center; gap:2px; margin-top:-2px;}}
      .char .legs div{{width:6px;height:9px;background:#3a2205;border-radius:2px; animation:walk .5s ease-in-out infinite;}}
      .char .legs div:nth-child(2){{animation-delay:.25s;}}
      @keyframes walk{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(2px);}}}}
      .cap-tag{{position:absolute; top:8px; left:12px; font-size:11px; color:#F4EFFF; background:rgba(0,0,0,.35); padding:3px 9px; border-radius:20px;}}
      .sky-icon{{position:absolute; top:8px; right:12px; font-size:18px;}}
    </style>
    <div class="street">
      <div class="cap-tag">STOP {round_number}/{total_rounds} · ◀ ▶ 走到门口敲门</div>
      <div class="sky-icon">{sky_icon}</div>
      {stars_html}
      <div class="track">
        {doors_html}
        {coins_html}
        <div class="char" style="left:{x}px;">
          <div class="cap"></div>
          <div class="head"></div>
          <div class="body"></div>
          <div class="legs"><div></div><div></div></div>
        </div>
      </div>
      <div class="ground"></div>
    </div>
    """
    components.html(html, height=height + 10)


def star_picker(key: str, label: str, scale: int = 7, icon: str = "★", default: int = 4) -> int:
    """Row of clickable icon buttons standing in for st.slider(1, scale).
    Returns the same 1..scale integer the original slider produced."""
    state_key = f"_stars_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = default
    st.caption(label)
    cols = st.columns(scale)
    for i in range(scale):
        active = (i + 1) <= st.session_state[state_key]
        if cols[i].button(icon, key=f"{key}_{i}", type="primary" if active else "secondary", use_container_width=True):
            st.session_state[state_key] = i + 1
            st.rerun()
    st.markdown(
        f"<div class='game-muted'>当前评分：{st.session_state[state_key]} / {scale}</div>",
        unsafe_allow_html=True,
    )
    return st.session_state[state_key]


def dialogue_box(speaker_emoji: str, speaker_name: str, text: str, page: int = 1, total_pages: int = 1) -> None:
    """RPG-style paged dialogue box. Purely a renderer; app.py owns the
    page counter in session_state and supplies the current page's text.
    """
    html = f"""
    <div class="dialogue-box">
      <div class="dialogue-head">
        <div class="dialogue-portrait">{speaker_emoji}</div>
        <div class="dialogue-name">{speaker_name}</div>
      </div>
      <div class="dialogue-text">{text}</div>
      <div class="dialogue-page">{page} / {total_pages}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def game_card(row: pd.Series, label: str, is_recommended: bool, group: str, explanation: str | None, type_labels: dict, landlord: Optional[dict] = None, locked: bool = False, round_number: int = 1, detailed: bool = False) -> None:
    highlight = is_recommended and group != "control"
    badge = "<span class='game-badge'>⭐ AI 推荐</span>" if highlight else ""
    score = f"<div class='game-muted'>推荐分数：{row['recommendation_score']:.1f}/100</div>" if highlight else ""
    landlord = landlord or landlord_for(1, label)
    landlord_tag = f"<div class='landlord-tag'>{landlord['emoji']} 房东：{landlord['name']}</div>"

    def shown(value, suffix="", digits=0):
        return "数据未提供" if pd.isna(value) else f"{value:.{digits}f}{suffix}"

    location = row.get("location_text") if pd.notna(row.get("location_text")) else row["district"]
    lock_note = "<div class='game-muted' style='color:var(--coral);'>🚶 走到门口才能敲门哦</div>" if locked else ""
    facilities = ["Wi-Fi", "厨房"]
    if float(row.get("area_sqm", 0) or 0) >= 35: facilities.append("阳台")
    if str(row.get("orientation", "")) in {"南", "东南", "南北"}: facilities.append("采光佳")
    facility_text = " · ".join(facilities)
    pro = "空间舒适，生活设施较完整" if float(row.get("area_sqm", 0) or 0) >= 30 else "小而温馨，日常打理轻松"
    con = "租金需要仔细规划" if float(row.get("monthly_rent", 0) or 0) > 6000 else "离核心商业区可能较远"
    html = f"""
    <div class="game-card {'recommended' if highlight else ''} {'locked' if locked else ''}">
      <div class="pxl" style="font-size:.68rem;">房源 {label}</div>
      {badge}
      {landlord_tag}
      <h4 style="margin:6px 0 2px;">{row['title']}</h4>
      <div class="game-muted">{location} · {type_labels[row['rental_type']]}</div>
      <div class="game-price">¥{int(row['monthly_rent']):,}<small style="font-size:.9rem;">/月</small></div>
      {score}
      <p style="font-size:.85rem; line-height:1.7; margin-top:8px;">
        🚇 地铁距离：{shown(row['metro_distance_m'], ' 米')}<br>
        📐 面积：{shown(row['area_sqm'], '㎡')} · 卧室：{shown(row['bedrooms'], '间')}<br>
        🧭 朝向：{row.get('orientation') if pd.notna(row.get('orientation')) else '数据未提供'}
      </p>
      <p style="font-size:.82rem; color:#cfc4ea;">{row['short_description']}</p>
      <div class='game-muted'>🛜 {facility_text}</div>
      <div class='pros-cons'><div class='pro'>优点 · {pro}</div><div class='con'>注意 · {con}</div></div>
      {lock_note}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def property_detail(row: pd.Series, label: str, day: int, type_labels: dict, landlord: dict) -> None:
    room_assets = {1:"living-sage-v1.png",2:"bedroom-cream-v1.png",3:"studio-blue-v1.png",4:"living-sage-v1.png",5:"bedroom-cream-v1.png",6:"studio-blue-v1.png"}
    art = _asset_data_url(f"assets/image2/{room_assets.get(day, 'living-sage-v1.png')}")
    location = row.get("location_text") if pd.notna(row.get("location_text")) else row["district"]
    area = float(row.get("area_sqm", 0) or 0)
    rent = int(row.get("monthly_rent", 0) or 0)
    suitable = "喜欢安静、自然与独处的人" if day in {1,2,5} else "重视便利、邻里与城市生活的人"
    unsuitable = "追求高密度商业与夜生活的人" if day in {1,2,5} else "非常在意绝对安静环境的人"
    layout = f"{int(row.get('bedrooms', 0) or 0)}室 · {type_labels.get(row.get('rental_type'), '住宅')}"
    st.markdown(
        f"""<div class='property-detail-shell'><div class='detail-art' style=\"background-image:url('{art}')\"></div>
        <div class='property-copy'><div class='pxl'>房源 {label}</div><h2>{row['title']}</h2><p class='game-muted'>📍 {location} · {type_labels.get(row.get('rental_type'), '住宅')}</p>
        <div class='game-price'>¥{rent:,}<small>/月</small></div>
        <div class='property-meta'><span>📐 {area:.0f}㎡</span><span>🏠 {layout}</span><span>🚇 地铁 {float(row.get('metro_distance_m',0) or 0):.0f}米</span><span>🧭 {row.get('orientation') if pd.notna(row.get('orientation')) else '朝向未提供'}</span></div>
        <div class='property-review'><b>房源描述</b><br>{row.get('short_description','')}<br><span class='game-muted'>✅ 适合：{suitable}<br>🌙 不适合：{unsuitable}<br>{landlord['emoji']} {landlord['name']}：{landlord['line']}</span></div></div></div>""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Achievements — computed purely from data ALREADY collected in
# st.session_state.choices (the same rows written by save_choice).
# --------------------------------------------------------------------------

def compute_badges(choices: list[dict], preferences: Optional[dict]) -> list[dict]:
    if not choices:
        return []
    df = pd.DataFrame(choices)
    badges: list[dict] = []
    if (df["decision_time_seconds"] < 10).any():
        badges.append({"icon": "⚡", "title": "闪电决策", "desc": "10 秒内敲定过一套房"})
    if (df["satisfaction"] >= 6).all():
        badges.append({"icon": "😄", "title": "从不将就", "desc": "每一轮满意度都在 6 分以上"})
    if preferences and (df["chosen_rent"] <= preferences.get("budget_max", 1e9) * 0.7).mean() >= 0.5:
        badges.append({"icon": "🧮", "title": "精打细算", "desc": "过半选择低于预算的 70%"})
    if (df["recommendation_followed"] == True).mean() >= 0.8:  # noqa: E712
        badges.append({"icon": "🤖", "title": "信任 AI", "desc": "八成以上选择跟随了推荐"})
    if (df["recommendation_followed"] == True).mean() <= 0.2:  # noqa: E712
        badges.append({"icon": "🧭", "title": "自有主张", "desc": "很少直接采纳 AI 推荐"})
    if df["chosen_area"].mean() > 50:
        badges.append({"icon": "🛋️", "title": "宽敞党", "desc": "平均选房面积超过 50㎡"})
    if len(df) >= 6:
        badges.append({"icon": "🏁", "title": "全程通关", "desc": "走完了全部 6 站"})
    return badges


def badge_toast(new_badges: list[dict]) -> None:
    if not new_badges:
        return
    for b in new_badges:
        st.markdown(
            f"""<div style="background:var(--accent-soft); color:var(--ink); border:1.5px solid #d9a08f;
              border-radius:12px; padding:10px 14px; margin-bottom:8px; animation:popin .35s ease;">
              🎉 <b>解锁成就：{b['icon']} {b['title']}</b> — {b['desc']}
            </div>""",
            unsafe_allow_html=True,
        )


def badge_shelf(badges: list[dict]) -> None:
    if not badges:
        st.caption("本次旅程还没有解锁成就。")
        return
    pills = "".join(
        f"""<div class="badge-pill"><div class="ic">{b['icon']}</div><div class="t">{b['title']}</div><div class="d">{b['desc']}</div></div>"""
        for b in badges
    )
    st.markdown(f"<div class='badge-shelf'>{pills}</div>", unsafe_allow_html=True)


def level_clear_banner(round_number: int, total_rounds: int, coins_earned: int) -> None:
    """'Level clear' interstitial shown right after confirming a choice,
    before walking into the next round. Pure flavor/pacing."""
    st.markdown(
        f"""<div class="clear-banner">
          <div class="pxl" style="font-size:1.1rem;">🚩 第 {round_number}/{total_rounds} 站 · 通关！</div>
          <div class="game-muted" style="margin-top:8px;">本站获得 🪙 +{coins_earned} 积分</div>
        </div>""",
        unsafe_allow_html=True,
    )


def identity_card(avatar_id: Optional[str], coins: int, badges: list[dict], group_label: str) -> None:
    av = _avatar(avatar_id)
    html = f"""
    <div style="display:flex; gap:16px; align-items:center; background:#fffefa;
      border:1.5px solid var(--line); box-shadow:5px 6px 0 var(--paper-2); border-radius:16px; padding:16px 20px;">
      <div style="font-size:2.6rem;">{av['emoji']}</div>
      <div>
        <div class="pxl" style="font-size:.8rem;">{av['name']} · 落脚通关证</div>
        <div class="game-muted" style="margin-top:4px;">体验模式：{group_label}</div>
        <div class="game-muted">累计积分：🪙 {coins} · 成就数：🏅 {len(badges)}</div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def confetti_burst(height: int = 220) -> None:
    html = f"""
    <canvas id="confetti-canvas" style="width:100%;display:block;"></canvas>
    <script>
    (function(){{
      const c = document.getElementById('confetti-canvas');
      const ctx = c.getContext('2d');
      const W = c.parentElement.clientWidth || 400, H = {height};
      c.width = W; c.height = H;
      const colors = ['#FFD166','#FF6B5C','#6FCF97','#B7A9E0'];
      const pieces = Array.from({{length: 70}}, () => ({{
        x: Math.random()*W, y: -20 - Math.random()*H,
        vy: 2+Math.random()*3, vx: -1+Math.random()*2,
        size: 4+Math.random()*4, color: colors[Math.floor(Math.random()*colors.length)],
        rot: Math.random()*360
      }}));
      let frame = 0;
      function tick(){{
        ctx.clearRect(0,0,W,H);
        pieces.forEach(p=>{{
          p.y += p.vy; p.x += p.vx; p.rot += 4;
          ctx.save(); ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
          ctx.fillStyle = p.color; ctx.fillRect(-p.size/2,-p.size/2,p.size,p.size);
          ctx.restore();
        }});
        frame++;
        if(frame < 90) requestAnimationFrame(tick);
      }}
      tick();
    }})();
    </script>
    """
    components.html(html, height=height)


def sound_ping(kind: str = "coin") -> None:
    """Best-effort tiny beep via the Web Audio API. Browsers often block
    autoplay audio inside iframes without a direct gesture, so this is
    decorative and silently no-ops if blocked."""
    freq = {"coin": 880, "badge": 660, "knock": 220, "step": 340}.get(kind, 880)
    html = f"""
    <script>
    try {{
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const o = ctx.createOscillator(); const g = ctx.createGain();
      o.type = 'square'; o.frequency.value = {freq};
      g.gain.setValueAtTime(0.05, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.15);
      o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.15);
    }} catch (e) {{}}
    </script>
    """
    components.html(html, height=0)
