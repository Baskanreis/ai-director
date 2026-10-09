"""User-importable creative pack registry.

Packs are JSON manifests containing CreativeAsset-compatible rows. This keeps the
built-in library extensible without bundling proprietary third-party assets.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable
from .pro_asset_library import CreativeAsset

ALLOWED_KINDS={"effect","transition","motion","text","sfx","music","audio_fx","overlay","filter","sticker","template"}


def load_pack(path: str | Path) -> list[CreativeAsset]:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    rows=data.get("assets", data) if isinstance(data, dict) else data
    if not isinstance(rows, list): raise ValueError("Pack assets must be a list")
    out=[]
    for row in rows:
        if not isinstance(row, dict): continue
        kind=row.get("kind")
        if kind not in ALLOWED_KINDS: continue
        out.append(CreativeAsset(str(row["id"]),str(row.get("name",row["id"])),kind,tuple(row.get("tags",())),dict(row.get("params",{})),str(row.get("license","User Imported"))))
    return out


def save_pack(path: str | Path, assets: Iterable[CreativeAsset], name: str="AI Director Creative Pack", version: str="1.0") -> None:
    rows=[]
    for a in assets:
        rows.append({"id":a.id,"name":a.name,"kind":a.kind,"tags":list(a.tags),"params":a.params,"license":a.license})
    Path(path).write_text(json.dumps({"name":name,"version":version,"assets":rows},ensure_ascii=False,indent=2),encoding="utf-8")

__all__=["load_pack","save_pack","ALLOWED_KINDS"]
