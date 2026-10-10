# -*- coding: utf-8 -*-
"""Stylesheet for the platform page.

Editorial layout: a narrow measure for prose, figures that break out of it, and
a sticky contents rail. The page is long by nature - 52 candidates and 23
references - so the rail is not decoration, it is how the page gets used.

Typeface is IBM Plex, the trio the simulator already loads, so the two pages
read as one project: Serif for headings, Sans for prose, Mono for anything that
sits in a column of numbers.
"""

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=IBM+Plex+Mono:wght@400;500&"
         "family=IBM+Plex+Sans:wght@400;500;600&"
         "family=IBM+Plex+Serif:wght@500;600&display=swap")

CSS = """
*{box-sizing:border-box}
html{color-scheme:light dark;scroll-behavior:smooth}
body{margin:0;background:var(--plane);color:var(--ink-1);
     font:17px/1.7 var(--sans);-webkit-text-size-adjust:100%}
.shell{max-width:1200px;margin:0 auto;padding:0 28px 120px;
       display:grid;grid-template-columns:184px minmax(0,1fr);gap:0 56px}

.rail{grid-column:1;position:sticky;top:0;align-self:start;
      padding:40px 0;max-height:100vh;overflow-y:auto}
.rail ol{list-style:none;margin:0;padding:0}
.rail a{display:block;padding:5px 0 5px 12px;margin-left:-14px;
        color:var(--ink-3);text-decoration:none;font-size:13px;line-height:1.35;
        border-left:2px solid transparent;transition:color .15s,border-color .15s}
.rail a:hover{color:var(--ink-1)}
.rail a.on{color:var(--ink-1);border-left-color:var(--series-a);font-weight:500}
.railhead{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
          color:var(--ink-3);padding-left:12px;margin:0 0 10px}
.col{grid-column:2;min-width:0}
.prose{max-width:68ch}

header{padding:92px 0 8px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(38px,5.6vw,60px);
   line-height:1.04;margin:0 0 22px;letter-spacing:-.022em;max-width:17ch}
.lede{font-size:clamp(19px,2.1vw,22px);line-height:1.55;color:var(--ink-2);
      margin:0 0 16px;max-width:60ch}
.lede b{color:var(--ink-1);font-weight:600}
.sub{color:var(--ink-3);font-size:14px;line-height:1.6;margin:26px 0 0;max-width:62ch}
section{margin:88px 0 0;scroll-margin-top:28px}
h2{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
   color:var(--ink-3);margin:0 0 10px;font-weight:500}
.h2sub{font-family:var(--serif);font-weight:600;font-size:clamp(25px,3.1vw,34px);
       line-height:1.18;margin:0 0 20px;letter-spacing:-.015em;max-width:22ch}
h3{font-family:var(--serif);font-weight:600;font-size:18px;margin:38px 0 10px}
/* Prose keeps a readable measure; figures, tables and cards do not inherit it
   and run the full column. Without this the body text ran about 990px at 17px,
   which is roughly 110 characters a line - far past where the eye loses the
   return sweep. */
p{margin:0 0 16px}
section>p,header>p{max-width:68ch}
.aside{color:var(--ink-2);font-size:15px;line-height:1.65;max-width:66ch}
.empty{color:var(--ink-3);font-style:italic}
code{font-family:var(--mono);font-size:.86em;background:var(--surface-1);
     border:1px solid var(--ring);border-radius:4px;padding:1px 5px}
.card{background:var(--surface-1);border:1px solid var(--ring);border-radius:16px;
      padding:26px 28px;margin:26px 0}
.figure{margin:30px 0}

/* hero: one mark per candidate pair */
.herofig{margin:40px 0 0;padding:0}
svg.strip{width:100%;height:auto;display:block}
.figscroll svg.strip{min-width:560px}
.striplab{fill:var(--ink-2);font-size:12px;font-family:var(--sans)}
.herofig figcaption{margin-top:16px;color:var(--ink-3);font-size:13.5px;
                    line-height:1.6;max-width:62ch}

.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
       gap:0;margin:52px 0 0;border-top:1px solid var(--axis)}
.tile{padding:24px 28px 26px 0;border-right:1px solid var(--grid)}
.tile:last-child{border-right:none}
.tile-v{font-family:var(--mono);font-size:40px;line-height:1;font-weight:400;
        letter-spacing:-.03em}
.tile-k{font-family:var(--serif);font-weight:600;font-size:16px;
        color:var(--ink-1);margin-top:12px;line-height:1.3}
.tile-s{font-size:13px;color:var(--ink-3);margin-top:7px;line-height:1.5}

/* the one claim a reader should leave with */
.callout{margin:0 0 34px;padding:28px 30px;border-radius:16px;
         background:var(--surface-1);border:1px solid var(--ring);
         border-left:3px solid var(--critical)}
.callout-lead{font-family:var(--serif);font-weight:600;
              font-size:clamp(20px,2.4vw,26px);line-height:1.3;margin:0 0 12px;
              color:var(--ink-1);max-width:24ch;letter-spacing:-.01em}
.callout-body{margin:0;color:var(--ink-2);font-size:15px;line-height:1.65;
              max-width:64ch}
.callout-body i{font-style:italic;color:var(--ink-1)}

.lightbar{display:flex;height:10px;border-radius:5px;overflow:hidden;
          margin:6px 0 14px;gap:2px}
.lightbar span{display:block}
.lightbar .green{background:var(--good)}
.lightbar .yellow{background:var(--warning)}
.lightbar .red{background:var(--critical);opacity:.45}
.lightkey{display:flex;gap:22px;flex-wrap:wrap;font-size:13.5px;
          color:var(--ink-2);margin:0 0 24px}
.lightkey i{font-style:normal;font-family:var(--mono);color:var(--ink-1);
            font-weight:500}

svg.chart,svg.arch{width:100%;height:auto;display:block}
.grid{stroke:var(--grid);stroke-width:1}
.tick,.axis-title,.rowsub,.rownote,.ps,.ms{fill:var(--ink-3);font-size:11px;
      font-family:var(--sans)}
.tick,.rownote{font-family:var(--mono)}
.axis-title{font-size:12px;font-family:var(--sans)}
.rowlab,.mt{fill:var(--ink-1);font-size:13px;font-weight:600;font-family:var(--sans)}
.mb{fill:var(--ink-1);font-size:13px;font-family:var(--sans)}
.pl{fill:var(--ink-1);font-size:14px;font-weight:600;font-family:var(--serif)}
.range{opacity:.92}
.figscroll{overflow-x:auto;overscroll-behavior-x:contain}
.figscroll svg.chart{min-width:660px}
.figscroll svg.arch{min-width:600px}
.figscroll::-webkit-scrollbar{height:8px}
.figscroll::-webkit-scrollbar-thumb{background:var(--axis);border-radius:4px}
.swipe{display:none;color:var(--ink-3);font-size:12.5px;margin:10px 0 0}
@media (max-width:700px){.swipe{display:block}}

/* the two explanatory figures */
svg.mech,svg.enzfig{width:100%;height:auto;display:block}
.figscroll svg.mech{min-width:720px}
.figscroll svg.enzfig{min-width:740px}
.mechfig,.enzfigwrap{margin:28px 0 0;padding:0}
.mechfig figcaption,.enzfigwrap figcaption{margin-top:16px;color:var(--ink-3);
    font-size:13.5px;line-height:1.6;max-width:70ch}
.panlab{fill:var(--ink-3);font-size:11px;letter-spacing:.11em;
        text-transform:uppercase;font-family:var(--sans)}
.poolt{fill:var(--ink-1);font-size:14px;font-weight:600;font-family:var(--sans)}
.flow{fill:var(--ink-3);font-size:11.5px;font-family:var(--sans)}
.curve{fill:none;stroke:var(--ink-2);stroke-width:2}
.band{fill:var(--series-a);opacity:.13}
.ptlab{font-size:12.5px;font-weight:600;font-family:var(--sans)}
.ptsub{fill:var(--ink-3);font-size:11px;font-family:var(--sans)}
.note{fill:var(--ink-3);font-size:11.5px;font-family:var(--sans)}

table{border-collapse:collapse;width:100%;font-size:13.5px}
th{text-align:left;font-weight:500;color:var(--ink-3);font-size:11px;
   letter-spacing:.09em;text-transform:uppercase;padding:0 12px 10px;
   border-bottom:1px solid var(--axis);white-space:nowrap}
th .u{text-transform:none;letter-spacing:0}
td{padding:11px 12px;border-bottom:1px solid var(--grid);vertical-align:top}
td.n,th.n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;
          white-space:nowrap;font-size:13px}
td.bm{font-weight:600;white-space:nowrap}
td.ctx{color:var(--ink-2);font-size:12.5px}
td.why{color:var(--ink-2);font-size:12.5px;min-width:24ch}
.org{color:var(--ink-3);font-size:11.5px;font-style:italic}
tr.hid{display:none}
table.posdata{margin-top:18px;min-width:560px}
table.panels{min-width:620px}
table.enz{min-width:600px}

.chip{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;
      font-size:12px;font-weight:500}
.chip .dot{font-size:13px;line-height:1}
.chip.green{color:var(--good)}
.chip.yellow{color:#8a6100}
.chip.red{color:var(--critical)}
.tt{display:inline-grid;place-items:center;width:21px;height:21px;border-radius:7px;
    font-size:11.5px;font-weight:600;color:#fff;font-family:var(--sans)}
.tt.A{background:var(--series-a)}
.tt.B{background:var(--series-b)}
tr.v-holds td.bm{color:var(--good)}
tr.v-fails td.bm{color:var(--critical)}

.filters{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:0 0 18px;
         font-size:13.5px;color:var(--ink-2)}
select{font:inherit;font-size:13.5px;padding:6px 9px;border-radius:9px;
       border:1px solid var(--axis);background:var(--surface-1);color:var(--ink-1)}
.count{color:var(--ink-3);font-size:12.5px;font-family:var(--mono)}
[data-js-only]{display:none}
.more{margin:18px 0 0;font:inherit;font-size:13.5px;padding:9px 16px;
      border-radius:10px;border:1px solid var(--axis);background:var(--surface-1);
      color:var(--ink-1);cursor:pointer}
.more:hover{border-color:var(--ink-3)}

.cols{display:grid;grid-template-columns:1fr 1fr;gap:34px}
ul.gap{padding-left:20px;margin:10px 0;font-size:14.5px;color:var(--ink-2);
       line-height:1.6}
ul.gap li{margin:9px 0}
ol.refs{padding-left:26px;font-size:14px;color:var(--ink-2)}
ol.refs li{margin:12px 0;padding-left:4px}
ol.refs a{color:var(--series-a);text-decoration:none;font-family:var(--mono);
          font-size:13px;word-break:break-word}
ol.refs a:hover{text-decoration:underline}
.use{display:block;color:var(--ink-3);font-size:12.5px;margin-top:3px;line-height:1.5}
footer{margin:96px 0 0;padding-top:26px;border-top:1px solid var(--grid);
       color:var(--ink-3);font-size:13px;line-height:1.65;max-width:66ch}
footer a{color:var(--series-a)}

@media (max-width:980px){
  .shell{grid-template-columns:1fr;gap:0;padding:0 20px 90px}
  .rail{position:static;max-height:none;padding:22px 0 0;
        border-bottom:1px solid var(--grid)}
  .rail ol{display:flex;gap:18px;overflow-x:auto;padding-bottom:12px}
  .rail a{border-left:none;padding-left:0;margin-left:0;white-space:nowrap}
  .rail a.on{border-left:none;color:var(--series-a)}
  .railhead{display:none}
  .col{grid-column:1}
  header{padding:40px 0 4px}
  section{margin:64px 0 0}
  .cols{grid-template-columns:1fr;gap:26px}
  /* stacked, the column rule becomes a stray vertical line beside each tile */
  .tile{border-right:none;border-bottom:1px solid var(--grid);
        padding:22px 0 24px}
  .tile:last-child{border-bottom:none}
  .callout{padding:22px 20px}
}
"""
