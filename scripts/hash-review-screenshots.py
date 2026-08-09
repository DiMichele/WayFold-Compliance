"""Compute SHA256 for docs/review screenshot packs."""
import hashlib
import json
import pathlib

base = pathlib.Path(__file__).resolve().parents[1] / "docs" / "review"
out = []
for pack in ("realign", "final"):
    p = base / pack
    if not p.exists():
        continue
    for f in sorted(p.glob("*.png")):
        data = f.read_bytes()
        out.append(
            {
                "pack": pack,
                "file": f.name,
                "path": f.as_posix().split("wayfold-compliance/", 1)[-1],
                "image_sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
print(json.dumps(out, indent=2))
