#!/bin/sh
# Download the Vampire prover (Linux x86-64) into tools/. Lean comes from elan (see lean/lean-toolchain).
set -e
cd "$(dirname "$0")/.."
mkdir -p tools
curl -sSfL -o tools/vampire.zip https://github.com/vprover/vampire/releases/download/v5.1.0/vampire-Linux-X64.zip
python3 -c "import zipfile; zipfile.ZipFile('tools/vampire.zip').extractall('tools')"
chmod +x tools/vampire
rm tools/vampire.zip
tools/vampire --version
