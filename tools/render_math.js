/*
 * Render the page's equations with KaTeX, once, at build time.
 *
 * Reads {name: tex} as JSON on stdin and writes {name: html} on stdout. The
 * result is cached in data/katex.json and committed, so an ordinary page build
 * needs neither Node nor KaTeX installed - only a change to an equation does.
 *
 * Rendering here rather than in the browser means the maths is in the markup:
 * it is there with JavaScript off, it is there in print, and a reader with a
 * screen reader gets the MathML KaTeX emits alongside the visual output.
 *
 *     node tools/render_math.js < in.json > out.json
 */
const katex = require("katex");

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { raw += d; });
process.stdin.on("end", () => {
  const input = JSON.parse(raw);
  const out = {};
  for (const [name, item] of Object.entries(input)) {
    const tex = typeof item === "string" ? item : item.tex;
    const display = typeof item === "string" ? true : !!item.display;
    try {
      out[name] = katex.renderToString(tex, {
        displayMode: display,
        output: "htmlAndMathml",
        throwOnError: true,
        strict: "warn",
        trust: false,
      });
    } catch (e) {
      process.stderr.write("FAILED " + name + ": " + e.message + "\n");
      process.exit(1);
    }
  }
  process.stdout.write(JSON.stringify(out, null, 1));
});
