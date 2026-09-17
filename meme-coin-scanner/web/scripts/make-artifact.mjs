/**
 * Rewrites the Vite build's index.html into a page body that can be
 * published as a Claude Artifact.
 *
 * The Artifact host wraps whatever it is given in its own
 * <!doctype>/<html>/<head>/<body> skeleton, so the published file must
 * carry only the page's own head tags and markup.
 *
 * Usage: node scripts/make-artifact.mjs   (after `npm run build`)
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(resolve(root, "dist/index.html"), "utf8");

function requireMatch(pattern, description) {
  const match = html.match(pattern);
  if (!match) throw new Error(`No se encontró ${description} en dist/index.html`);
  return match[0];
}

const title = requireMatch(/<title>[\s\S]*?<\/title>/, "el <title>");
const fontLinks = html.match(/<link[^>]+fonts\.(googleapis|gstatic)\.com[^>]*>/g) ?? [];
const styleLink = requireMatch(/<link[^>]+rel="stylesheet"[^>]+assets\/[^>]*>/, "el CSS compilado");
const moduleScript = requireMatch(/<script[^>]+type="module"[^>]+><\/script>/, "el bundle JS");

const page = [
  title,
  ...fontLinks,
  styleLink,
  '<div id="root"></div>',
  moduleScript,
  "",
].join("\n");

const outPath = resolve(root, "dist/artifact.html");
writeFileSync(outPath, page);
console.log(`Artifact page escrita en ${outPath} (${page.length} bytes)`);
