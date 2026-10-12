// Copia assets reais do RUMO (repositório raiz) para web/public.
// Rodado antes do dev e do build; public/ gerado não entra no Git.
import { cpSync, mkdirSync, existsSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const root = join(web, "..", "assets");
const pub = join(web, "public");

const copies = [
  ["fonts/Inter-Regular.ttf", "fonts/Inter-Regular.ttf"],
  ["fonts/Inter-Bold.ttf", "fonts/Inter-Bold.ttf"],
  ["fonts/Poppins-Bold.ttf", "fonts/Poppins-Bold.ttf"],
  ["fonts/OFL.txt", "fonts/OFL.txt"],
  ["character/look/bust", "character/bust"],
  ["character/look/catalog.json", "character/catalog.json"],
  ["character/items/96", "character/items"],
  ["RUMO.png", "favicon.png"],
];

for (const [from, to] of copies) {
  const src = join(root, from);
  if (!existsSync(src)) throw new Error(`asset ausente: ${src}`);
  const dest = join(pub, to);
  rmSync(dest, { recursive: true, force: true });
  mkdirSync(dirname(dest), { recursive: true });
  cpSync(src, dest, { recursive: true });
}

await import("./make-example-pdfs.mjs");

// Material de TESTE do leitor (não é aula): usado só no modo EXEMPLO.
const fixture = join(web, "..", "tests", "fixtures", "campo-teste", "arquivos");
mkdirSync(join(pub, "pdf"), { recursive: true });
cpSync(join(fixture, "leitor-teste-2.0.0.pdf"), join(pub, "pdf", "exemplo-leitor.pdf"));
console.log("assets copiados para web/public");
