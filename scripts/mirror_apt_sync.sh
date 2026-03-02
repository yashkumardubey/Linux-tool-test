#!/bin/bash
# Template script to sync Ubuntu repos to an internal mirror host.
# Requires apt-mirror or rsync; adjust paths and suites as needed.

set -euo pipefail

MIRROR_BASE=/srv/apt-mirror
DEBIAN_MIRROR=http://archive.ubuntu.com/ubuntu
SUITES=(focal focal-updates focal-security)
ARCH=amd64

mkdir -p "$MIRROR_BASE"

# Example using apt-mirror config file approach -> run apt-mirror
# You can also use rsync from a mirror or use debmirror.

cat > /etc/apt/mirror.list <<EOF
set base_path    $MIRROR_BASE
set nthreads     20
set _tilde 0

# Ubuntu main
deb $DEBIAN_MIRROR focal main restricted universe multiverse
deb $DEBIAN_MIRROR focal-updates main restricted universe multiverse
deb $DEBIAN_MIRROR focal-security main restricted universe multiverse
EOF

# Run apt-mirror (requires apt-mirror installed and configured)
# apt-mirror /etc/apt/mirror.list

# Alternatively, sync specific pools via rsync (example):
# rsync -a --delete rsync://rsync.archive.ubuntu.com/ubuntu/ $MIRROR_BASE/ubuntu/

# After mirror is populated, serve it via Apache/Nginx and ensure Release and GPG keys are available.

echo "Mirror sync template complete. Customize and run apt-mirror or rsync as needed."
