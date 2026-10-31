#!/usr/bin/env python3
"""Read-only verification of the three historical ICOS/EUF source transfers."""
import argparse
import hashlib
import zlib
from pathlib import Path

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
SITES = {
    "DE-Lnf": ("EUF_DE-Lnf_FLUXNET_2002-2024_v1.3_r1", "695d801e041f6783a7b10d12f018d3675cf04194f242c84e39a15d178944c3ca", "EUF_DE-Lnf_FLUXNET_FLUXMET_HH_2002-2024_v1.3_r1.csv", 506471201, "5701d7ae"),
    "ES-LJu": ("EUF_ES-LJu_FLUXNET_2004-2024_v1.3_r1", "a04e6f9bc5d65f26dd314623f4756bd8ccaf0fa01a435419512cc56d547974ae", "EUF_ES-LJu_FLUXNET_FLUXMET_HH_2004-2024_v1.3_r1.csv", 411359064, "1b0caf16"),
    "GF-Guy": ("ICOS_GF-Guy_FLUXNET_2004-2025_v1.3_r1", "99607450a793005e842d0115fbc942ab93a6d93dab24b9795508852b89fc4b7b", "ICOS_GF-Guy_FLUXNET_FLUXMET_HH_2004-2025_v1.3_r1.csv", 506489883, "da625834"),
}


def checksum(path):
    h = hashlib.sha256(); crc = 0
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block); crc = zlib.crc32(block, crc)
    return h.hexdigest(), f"{crc & 0xffffffff:08x}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sites-root", type=Path, default=ROOT)
    a = ap.parse_args()
    mismatch = False
    for site, (release, expected_sha, filename, size, crc) in SITES.items():
        package = a.sites_root / site / "forcing/packages" / (release + ".zip")
        raw = a.sites_root / site / "forcing/raw" / release / filename
        print("SITE", site, flush=True)
        if package.is_file():
            sha, _ = checksum(package); ok = sha == expected_sha; mismatch |= not ok
            print("  PACKAGE", "SHA256_MATCH" if ok else "SHA256_DIFFERENT", str(package), flush=True)
        else:
            print("  PACKAGE ZIP_NOT_FOUND (may have been transferred as a directory)", str(package), flush=True)
        if raw.is_file():
            _, raw_crc = checksum(raw); ok = raw.stat().st_size == size and raw_crc == crc; mismatch |= not ok
            print("  RAW", "SIZE_AND_CRC32_MATCH" if ok else "SIZE_OR_CRC32_DIFFERENT", str(raw), flush=True)
        else:
            print("  RAW NOT_FOUND", str(raw), flush=True)
    print("READ-ONLY CHECK: CRC32 is an accidental-corruption check, not a cryptographic hash.")
    return int(mismatch)


if __name__ == "__main__": raise SystemExit(main())

