"use strict";

const { spawnSync } = require("child_process");

const CANDIDATES =
  process.platform === "win32" ? ["py -3", "py", "python", "python3"] : ["python3", "python"];

function tryCandidate(cmd) {
  const [exe, ...args] = cmd.split(" ");
  const result = spawnSync(exe, [...args, "--version"], { stdio: "ignore" });
  return result.status === 0;
}

/** Find a usable Python 3 interpreter command, or null if none found. */
function findPython() {
  for (const candidate of CANDIDATES) {
    if (tryCandidate(candidate)) {
      return candidate;
    }
  }
  return null;
}

module.exports = { findPython };
