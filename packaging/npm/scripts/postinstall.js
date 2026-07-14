"use strict";

const { spawnSync } = require("child_process");
const { findPython } = require("./find-python");

const PACKAGE_VERSION = require("../package.json").version;

function main() {
  const found = findPython();
  if (!found || found.tooOld) {
    const detail = found
      ? `Python ${found.tooOld} was found, but PortSlayer needs 3.9 or newer.`
      : "No Python was found on your PATH.";
    console.warn(
      `\n[portslayer] Python 3.9+ is required. ${detail}\n` +
        "  PortSlayer's engine is written in Python — install Python from\n" +
        "  https://python.org/downloads and re-run `npm install -g @appestox/portslayer`.\n"
    );
    return;
  }

  const python = found.command;
  const [exe, ...baseArgs] = python.split(" ");
  console.log(`[portslayer] Installing Python engine via ${python} -m pip …`);
  const result = spawnSync(
    exe,
    [...baseArgs, "-m", "pip", "install", "--upgrade", `portslayer==${PACKAGE_VERSION}`],
    { stdio: "inherit" }
  );

  if (result.status !== 0) {
    console.warn(
      "\n[portslayer] Automatic pip install failed. Install it yourself with:\n" +
        `  ${python} -m pip install --upgrade portslayer==${PACKAGE_VERSION}\n`
    );
  }
}

main();
