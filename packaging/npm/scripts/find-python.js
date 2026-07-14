"use strict";

const { spawnSync } = require("child_process");

const MIN_VERSION = [3, 9];

const CANDIDATES =
  process.platform === "win32" ? ["py -3", "py", "python", "python3"] : ["python3", "python"];

function candidateVersion(cmd) {
  const [exe, ...args] = cmd.split(" ");
  const result = spawnSync(exe, [...args, "--version"], { encoding: "utf8" });
  if (result.status !== 0) {
    return null;
  }
  const match = /Python (\d+)\.(\d+)/.exec(`${result.stdout} ${result.stderr}`);
  return match ? [Number(match[1]), Number(match[2])] : null;
}

function isSupported(version) {
  const [major, minor] = version;
  return major > MIN_VERSION[0] || (major === MIN_VERSION[0] && minor >= MIN_VERSION[1]);
}

/**
 * Find a usable Python >= 3.9 interpreter command.
 * Returns { command } on success, { tooOld } when only an older Python
 * exists, or null when no Python is found at all.
 */
function findPython() {
  let tooOld = null;
  for (const candidate of CANDIDATES) {
    const version = candidateVersion(candidate);
    if (!version) {
      continue;
    }
    if (isSupported(version)) {
      return { command: candidate };
    }
    tooOld = tooOld || `${version[0]}.${version[1]}`;
  }
  return tooOld ? { tooOld } : null;
}

module.exports = { findPython, MIN_VERSION };
