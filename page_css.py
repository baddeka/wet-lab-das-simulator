# -*- coding: utf-8 -*-
"""Stylesheet for the platform page.

Editorial layout: a narrow measure for prose, figures that break out of it, and
a sticky contents rail. The page is long by nature - 52 candidates and 23
references - so the rail is not decoration, it is how the page gets used.

Dressed in the team wiki's own design: Fraunces over Space Grotesk on a night
background, the firefly accent, the eyebrow-and-title heading pair, and the
film grain that keeps large dark areas from banding. The tokens are copied from
the wiki rather than matched by eye - see PALETTE in render_page.py.

Everything is served from this repository. The fonts are the wiki's own files,
the maths is KaTeX rendered at build time with its stylesheet and woff2 beside
it, and nothing is fetched from a CDN: iGEM requires every asset to come from
iGEM infrastructure, and this page should be able to move there unchanged.
"""

# A real stylesheet now rather than a Google Fonts URL. It carries the KaTeX
# rules; the typefaces are declared below, next to the rest of the CSS.
FONTS = "assets/katex/katex.css"

CSS = """
@font-face{font-family:"Fraunces";src:url("assets/fonts/Fraunces-var.woff2")
  format("woff2");font-weight:100 900;font-style:normal;font-display:swap}
@font-face{font-family:"Fraunces";
  src:url("assets/fonts/Fraunces-Italic-var.woff2") format("woff2");
  font-weight:100 900;font-style:italic;font-display:swap}
@font-face{font-family:"Space Grotesk";
  src:url("assets/fonts/SpaceGrotesk-var.woff2") format("woff2");
  font-weight:300 700;font-style:normal;font-display:swap}

*{box-sizing:border-box}
html{color-scheme:dark;scroll-behavior:smooth;background:var(--dusk-950)}
body{margin:0;background:var(--dusk-950);color:var(--ink-1);
     font:17px/1.72 var(--sans);-webkit-text-size-adjust:100%;
     -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}

/* faint film grain over everything - the wiki's, and for the same reason:
   a page this dark bands without it */
body::after{content:"";position:fixed;inset:0;z-index:3000;pointer-events:none;
  opacity:.05;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
::selection{background:rgba(217,247,107,.85);color:var(--dusk-950)}
:focus-visible{outline:2px solid var(--firefly);outline-offset:3px;
  border-radius:2px}
a{color:var(--sand-200);text-underline-offset:3px;transition:color .15s ease}
a:hover{color:var(--firefly)}
.shell{max-width:1200px;margin:0 auto;padding:0 28px 120px;
       display:grid;grid-template-columns:184px minmax(0,1fr);gap:0 56px}

.rail{grid-column:1;position:sticky;top:0;align-self:start;
      padding:40px 0;max-height:100vh;overflow-y:auto}
.rail ol{list-style:none;margin:0;padding:0}
.rail a{display:block;padding:5px 0 5px 12px;margin-left:-14px;
        color:var(--ink-3);text-decoration:none;font-size:13px;line-height:1.35;
        border-left:2px solid transparent;transition:color .15s,border-color .15s}
.rail a:hover{color:var(--ink-1)}
.rail a.on{color:var(--firefly);border-left-color:var(--firefly);
           font-weight:500}
.railhead{font-size:11px;letter-spacing:.14em;text-transform:uppercase;
          color:var(--ink-3);padding-left:12px;margin:0 0 10px}
.col{grid-column:2;min-width:0}
.prose{max-width:68ch}

header{padding:92px 0 8px}
h1{font-family:var(--serif);font-weight:560;font-size:clamp(38px,5.6vw,60px);
   line-height:1.05;margin:0 0 22px;letter-spacing:-.015em;max-width:17ch}
.lede{font-size:clamp(19px,2.1vw,22px);line-height:1.55;color:var(--ink-2);
      margin:0 0 16px;max-width:60ch}
.lede b{color:var(--ink-1);font-weight:600}
.sub{color:var(--ink-3);font-size:14px;line-height:1.6;margin:26px 0 0;max-width:62ch}
section{margin:88px 0 0;scroll-margin-top:28px}
h2{font-size:11.5px;letter-spacing:.24em;text-transform:uppercase;
   color:var(--rust-500);margin:0 0 12px;font-weight:600}
.h2sub{font-family:var(--serif);font-weight:560;font-size:clamp(25px,3.1vw,34px);
       line-height:1.2;margin:0 0 20px;letter-spacing:-.01em;max-width:22ch}
.h2sub em,.h2sub .accent{font-style:italic;color:var(--firefly)}
h3{font-family:var(--serif);font-weight:560;font-size:19px;margin:38px 0 10px}
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
.card{background:var(--surface-1);border:1px solid var(--ring);
      border-radius:16px;padding:26px 28px;margin:26px 0}
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
table.lib{min-width:720px}
/* the verdict and type columns carry a chip, not prose */
.c-v{width:76px} .c-t{width:46px}
tr.r-main td{border-bottom:none;padding-bottom:4px}
tr.r-why td{border-bottom:1px solid var(--grid);padding:0 12px 12px;
            color:var(--ink-3);font-size:12.5px;line-height:1.5}
td.ctx{white-space:nowrap}
td.pos{color:var(--ink-2);white-space:nowrap}

.chip{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;
      font-size:12px;font-weight:500}
.chip .dot{font-size:13px;line-height:1}
.chip.green{color:var(--good)}
.chip.yellow{color:var(--warning)}
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
ol.refs a{color:var(--sand-200);text-decoration:none;font-family:var(--mono);
          font-size:13px;word-break:break-word}
ol.refs a:hover{text-decoration:underline}
.use{display:block;color:var(--ink-3);font-size:12.5px;margin-top:3px;line-height:1.5}
footer{margin:96px 0 0;padding-top:26px;border-top:1px solid var(--grid);
       color:var(--ink-3);font-size:13px;line-height:1.65;max-width:66ch}
footer a{color:var(--sand-200)}

/* ---------------------------------------------------------------- numbering
   One figure sequence across the whole document, and numbered sections. That
   is what makes a long page citable: "Figure 9" is a reference a reader can
   act on, "the chart above" is not. */
.secno{font-family:var(--mono);color:var(--rust-500);font-weight:500;
       margin-right:.7em;letter-spacing:0}
h3 .secno{color:var(--ink-3);font-size:.88em}
.h3sub{color:var(--ink-2);font-size:14.5px;line-height:1.6;max-width:66ch;
       margin:0 0 14px}

/* two-level contents rail */
.rail ol ol{margin:2px 0 8px}
.rail ol ol a{font-size:12px;padding:3px 0 3px 22px;color:var(--ink-3)}
.rail .num{font-family:var(--mono);opacity:.55;margin-right:.5em}

/* ------------------------------------------------------------------ figures */
figure.fig{margin:30px 0 34px;padding:0}
figure.fig figcaption,figure.tbl figcaption{color:var(--ink-2);font-size:13.5px;
    line-height:1.6;max-width:74ch;margin:14px 0 0}
figure.tbl figcaption{margin:0 0 14px}
figure.fig figcaption b,figure.tbl figcaption b{color:var(--ink-1);
    font-family:var(--sans);font-weight:600;white-space:nowrap}
.fignote{color:var(--ink-3);font-size:12.5px;line-height:1.55;max-width:70ch;
         margin:8px 0 0}
figure.tbl{margin:30px 0 34px;padding:0}
.scroll{overflow-x:auto;overscroll-behavior-x:contain}
.scroll::-webkit-scrollbar{height:8px}
.scroll::-webkit-scrollbar-thumb{background:var(--axis);border-radius:4px}

/* chart furniture, shared by every figure charts.py draws */
svg.chart{width:100%;height:auto;display:block}
.figscroll svg.chart{min-width:620px}
line.grid{stroke:var(--grid);stroke-width:1}
line.gridmin{stroke:var(--grid);stroke-width:1;opacity:.45}
line.spine{stroke:var(--axis);stroke-width:1.2}
line.tickmark{stroke:var(--axis);stroke-width:1.2}
text.tick{fill:var(--ink-3);font-size:11px;font-family:var(--mono);
          font-variant-numeric:tabular-nums}
text.axt{fill:var(--ink-2);font-size:12px;font-family:var(--sans)}
text.lgd{fill:var(--ink-1);font-size:12.5px;font-family:var(--sans)}
text.lgdsub{fill:var(--ink-3);font-size:11.5px;font-family:var(--sans)}
text.note{fill:var(--ink-3);font-size:11.5px;font-family:var(--sans)}
text.chord{fill:var(--critical);font-size:11.5px;font-weight:600;
           font-family:var(--mono)}
text.ptlab{fill:var(--ink-1);font-size:12.5px;font-weight:600;
           font-family:var(--sans)}
text.ptsub{fill:var(--ink-3);font-size:11px;font-family:var(--sans)}
text.rowlab2{fill:var(--ink-1);font-size:12.5px;font-family:var(--sans)}
text.rownote2{fill:var(--ink-3);font-size:11px;font-family:var(--mono);
              font-variant-numeric:tabular-nums}
text.grphd{fill:var(--ink-3);font-size:10.5px;letter-spacing:.12em;
           text-transform:uppercase;font-family:var(--sans)}
text.holds{fill:var(--good);font-size:11px;font-family:var(--sans)}
text.breaks{fill:var(--critical);font-size:11px;font-weight:600;
            font-family:var(--sans)}

/* ---------------------------------------------------------------- equations
   Written in HTML rather than loaded as a maths library: there are nine of
   them, none is more than one line deep, and a third of a megabyte of
   dependency to set one fraction is not a trade worth making on a page that
   has to load over a conference wifi. */
.eq{margin:20px 0;padding:22px 24px;background:var(--surface-1);
    border:1px solid var(--ring);border-radius:12px;overflow-x:auto;
    overscroll-behavior-x:contain}
.eq::-webkit-scrollbar{height:8px}
.eq::-webkit-scrollbar-thumb{background:var(--axis);border-radius:4px}
.eq .katex-display{margin:0}
.eq .katex-display+.katex-display{margin-top:14px}
.eq .katex{color:var(--ink-1);font-size:1.06em}
/* KaTeX sets its own colour nowhere, so the rules it draws - fraction bars,
   square-root overbars - inherit currentColor and come out right on the night
   background without touching katex.css */
dl.where+p,dl.where+.aside{margin-top:18px}
/* KaTeX sizes a symbol relative to its context, and the context here is a
   13px definition term, which left the symbols noticeably smaller than the
   equation they came out of */
dl.where dt .katex{font-size:15.5px;color:var(--ink-1)}
dl.where{margin:14px 0 0;font-size:14px;color:var(--ink-2);line-height:1.6;
         display:grid;grid-template-columns:auto 1fr;gap:6px 16px;
         max-width:72ch;align-items:baseline}
dl.where dt{font-size:13px;color:var(--ink-1);white-space:nowrap;
            padding-top:1px}
dl.where dd{margin:0}
.eqlab{display:block;color:var(--ink-3);font-size:11px;letter-spacing:.11em;
       text-transform:uppercase;margin:0 0 10px;font-family:var(--sans)}

/* ------------------------------------------------------- parameter tables */
table.params{min-width:840px}
table.params td.nm{font-family:var(--mono);font-size:12.5px;white-space:nowrap;
                   color:var(--ink-1)}
table.params td.pnote{color:var(--ink-3);font-size:12px;line-height:1.5;
                      min-width:28ch}
table.params td.u{color:var(--ink-3);font-size:12px;white-space:nowrap}
.kind{display:inline-block;font-size:10.5px;letter-spacing:.07em;
      text-transform:uppercase;padding:3px 7px;border-radius:5px;
      font-weight:600;white-space:nowrap;font-family:var(--sans)}
.kind.measured{background:rgba(95,191,123,.15);color:var(--good)}
.kind.derived{background:rgba(92,123,240,.17);color:#9db1f7}
.kind.assumed{background:rgba(224,170,92,.15);color:var(--warning)}
.kind.chosen,.kind.definition{background:var(--plane);color:var(--ink-3)}
tr.grphead td{background:var(--plane);font-size:10.5px;letter-spacing:.12em;
              text-transform:uppercase;color:var(--ink-3);font-weight:600;
              padding:9px 12px}

/* ------------------------------------------------------------- citations */
a.cite{font-family:var(--mono);font-size:.74em;vertical-align:.42em;
       color:var(--sand-200);text-decoration:none;padding:0 .08em;
       font-weight:500}
a.cite:hover{color:var(--firefly)}
a.cite:hover{text-decoration:underline}
ol.refs li{scroll-margin-top:90px}
ol.refs li:target{background:rgba(217,247,107,.08);border-radius:6px;
                  padding:6px 8px 6px 4px;margin-left:-8px}

/* a finding that contradicts something this project previously asserted */
.flag{margin:22px 0;padding:18px 22px;border-radius:12px;
      background:var(--surface-1);border:1px solid var(--ring);
      border-left:3px solid var(--warning)}
.flag p{margin:0;font-size:14.5px;line-height:1.65;color:var(--ink-2);
        max-width:68ch}
.flag p+p{margin-top:12px}
.flag b{color:var(--ink-1)}
.flag .h{display:block;font-size:11px;letter-spacing:.12em;
         text-transform:uppercase;color:var(--warning);margin:0 0 8px;
         font-weight:600}

/* a reference from the prose to a numbered figure or table */
a.xref{color:var(--sand-200);text-decoration:none;white-space:nowrap;
       border-bottom:1px solid rgba(236,201,138,.3)}
a.xref:hover{color:var(--firefly);border-bottom-color:var(--firefly)}

/* ------------------------------------------------------------- tooltips */
.tip{position:fixed;z-index:50;display:none;pointer-events:none;
     background:var(--ink-1);color:var(--surface-1);font:12.5px/1.45 var(--sans);
     padding:7px 10px;border-radius:7px;max-width:280px;
     box-shadow:0 4px 14px rgba(0,0,0,.18)}
[data-tip]{cursor:crosshair}

/* ---------------------------------------------------------------- print
   Judges print. Without this the contents rail takes a column on every sheet,
   the scrolling wrappers clip their figures at the viewport width, and figures
   break across pages in the middle of an axis. */
@media print{
  @page{margin:14mm}
  html,body{background:#fff;color:#000}
  .shell{display:block;max-width:none;padding:0}
  .rail,.filters,.more,.swipe,.tip{display:none!important}
  .col{grid-column:auto}
  .figscroll,.scroll{overflow:visible!important}
  .figscroll svg,.scroll table{min-width:0!important}
  svg{max-width:100%!important}
  figure.fig,figure.tbl,.eq,.callout,.flag,.card{break-inside:avoid;
      page-break-inside:avoid}
  h2,h3{break-after:avoid;page-break-after:avoid}
  section{break-before:auto;margin-top:34px}
  tr{break-inside:avoid}
  a{color:#000;text-decoration:none}
  /* a printed citation is useless as a link, so print where it points */
  ol.refs a::after{content:" (doi.org)";color:#555;font-size:.9em}
  .tiles{border-top:1px solid #999}
  header{padding-top:0}
}

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
  .eq .l{font-size:12.5px}
  dl.where{grid-template-columns:1fr;gap:2px 0}
  dl.where dd{margin:0 0 10px}
  figure.fig,figure.tbl{margin:22px 0 26px}
  .rail ol ol{display:none}
}
"""
