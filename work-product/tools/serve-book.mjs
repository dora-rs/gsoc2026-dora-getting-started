import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const root = resolve(__dirname, "..", "book");
const args = new Map();

for (let i = 2; i < process.argv.length; i += 1) {
  if (process.argv[i] === "--port" || process.argv[i] === "-p") {
    args.set("port", process.argv[i + 1]);
    i += 1;
  }
}

const port = Number(args.get("port") || process.env.PORT || 3000);

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ttf": "font/ttf",
  ".woff2": "font/woff2",
};

function resolveRequest(url) {
  const parsed = new URL(url, `http://localhost:${port}`);
  const decoded = decodeURIComponent(parsed.pathname);
  const relative = decoded === "/" ? "/index.html" : decoded;
  const candidate = normalize(join(root, relative));

  if (candidate !== root && !candidate.startsWith(root + sep)) {
    return null;
  }

  if (existsSync(candidate) && statSync(candidate).isDirectory()) {
    return join(candidate, "index.html");
  }

  return candidate;
}

const server = createServer((request, response) => {
  const file = resolveRequest(request.url || "/");

  if (!file || !existsSync(file) || !statSync(file).isFile()) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }

  response.writeHead(200, {
    "content-type": contentTypes[extname(file)] || "application/octet-stream",
  });
  createReadStream(file).pipe(response);
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Serving ${root}`);
  console.log(`Open http://localhost:${port}/`);
});
