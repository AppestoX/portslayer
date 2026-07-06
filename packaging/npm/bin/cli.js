#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const { findPython } = require("../scripts/find-python");

function main() {
  const python = findPython();
  if (!python) {
    console.error(
      "[portslayer] Python 3.10+ is required but was not found on your PATH.\n" +
        "Install it from https://python.org/downloads, then run:\n" +
        "  npm install -g @appestox/portslayer"
    );
    process.exit(1);
  }

  const [exe, ...baseArgs] = python.split(" ");
  const args = process.argv.slice(2);
  const result = spawnSync(exe, [...baseArgs, "-m", "portslayer.cli", ...args], {
    stdio: "inherit",
  });

  if (result.error) {
    console.error(`[portslayer] Failed to launch: ${result.error.message}`);
    process.exit(1);
  }
  process.exit(result.status === null ? 1 : result.status);
}

main();
