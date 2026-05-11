import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(__dirname, "../../../backend");
const child = spawn("python", ["app.py"], {
  cwd: backendDir,
  env: {
    ...process.env,
    APP_CONFIG_PATH: "config.e2e.yaml",
    APP_PORT: "5011",
  },
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => process.exit(code ?? 0));
