import { execSync } from "node:child_process";
import { rmSync } from "node:fs";
import { resolve } from "node:path";

const devProcessPattern = `${process.cwd()}/node_modules/.bin/next dev`;

try {
  execSync(`pkill -f "${devProcessPattern}"`, { stdio: "ignore" });
} catch {
  // No matching dev process is fine.
}

rmSync(resolve(process.cwd(), ".next"), { recursive: true, force: true });
