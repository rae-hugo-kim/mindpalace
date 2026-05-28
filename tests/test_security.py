"""Tests for mindpalace.security (disk-encryption guard helpers).

Detection is inherently best-effort and OS-dependent, so we unit-test
only the pure mount-table parser; the live ``detect_encryption`` walk is
exercised through the CLI guard tests with an injected detector.
"""
from mindpalace.security import _mount_device_for

_SAMPLE_MOUNTS = """\
/dev/sdb / ext4 rw,relatime 0 0
/dev/mapper/cryptdata /home/user/vault ext4 rw,relatime 0 0
tmpfs /tmp tmpfs rw,nosuid 0 0
drvfs /mnt/c 9p rw 0 0
"""


def test_mount_device_for_picks_longest_matching_mountpoint():
    """T17 (RED): the device of the most-specific mountpoint prefix wins."""
    # A path under /home/user/vault must map to the cryptdata device, not /.
    dev = _mount_device_for("/home/user/vault/mp.db", _SAMPLE_MOUNTS)
    assert dev == "/dev/mapper/cryptdata"


def test_mount_device_for_falls_back_to_root():
    """T17 (RED): a path not under any deeper mount maps to the root device."""
    dev = _mount_device_for("/var/lib/data/mp.db", _SAMPLE_MOUNTS)
    assert dev == "/dev/sdb"


def test_mount_device_for_handles_wsl_drvfs():
    """T17 (RED): a /mnt/c path resolves to the drvfs source (non-crypt)."""
    dev = _mount_device_for("/mnt/c/Users/rae/mp.db", _SAMPLE_MOUNTS)
    assert dev == "drvfs"
