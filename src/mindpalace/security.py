"""Disk-encryption guard (seed AC10).

The vault DB must live on an OS-encrypted volume (LUKS / FileVault /
BitLocker). Detection is inherently best-effort and platform-specific,
so ``detect_encryption`` returns a tri-state:

  True  -> positively confirmed encrypted
  False -> positively confirmed plain
  None  -> could not determine (unknown platform, parse failure)

The CLI guard treats both ``False`` and ``None`` as "not safe" and
blocks unless the user passes ``--accept-unencrypted`` — we never want
to silently persist a corpus in the clear.
"""
from __future__ import annotations

import os
import subprocess
import sys


def _mount_device_for(path: str, mounts_text: str) -> str | None:
    """Return the backing device for ``path`` from /proc/mounts text.

    Picks the mount whose mountpoint is the longest prefix of the
    absolute path — i.e. the most specific mount. Pure function so the
    matching logic is unit-testable without touching the live system.
    """
    abs_path = os.path.abspath(path)
    best_dev: str | None = None
    best_len = -1
    for line in mounts_text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        device, mountpoint = parts[0], parts[1]
        # Match mountpoint as a path prefix (with a boundary so /home does
        # not match /homeless).
        if abs_path == mountpoint or abs_path.startswith(mountpoint.rstrip("/") + "/"):
            if len(mountpoint) > best_len:
                best_dev = device
                best_len = len(mountpoint)
    return best_dev


def detect_encryption(path: str) -> bool | None:
    """Best-effort detection of whether ``path`` is on an encrypted volume.

    Linux only (the deployment target). Resolves the backing device via
    /proc/mounts, then asks lsblk whether the device's type chain
    contains a ``crypt`` node (LUKS / dm-crypt). Any uncertainty maps to
    ``None`` so the caller errs on the side of caution.
    """
    if not sys.platform.startswith("linux"):
        return None
    try:
        with open("/proc/mounts") as f:
            mounts = f.read()
    except OSError:
        return None

    device = _mount_device_for(path, mounts)
    if device is None:
        return None
    # Non-block-device sources (tmpfs, drvfs/9p on WSL, overlay) are not
    # encrypted volumes in the LUKS sense.
    if not device.startswith("/dev/"):
        return False

    try:
        out = subprocess.run(
            ["lsblk", "--noheadings", "--output", "TYPE", device],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None

    types = {line.strip() for line in out.stdout.splitlines() if line.strip()}
    if "crypt" in types:
        return True
    # We got a clean answer with no crypt layer.
    return False
