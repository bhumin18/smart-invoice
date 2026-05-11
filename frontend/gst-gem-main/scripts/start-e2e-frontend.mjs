import { spawn } from "node:child_process";

const child = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", "4174"], {
  env: {
    ...process.env,
    VITE_API_BASE: "http://127.0.0.1:5011/api",
  },
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => process.exit(code ?? 0));
