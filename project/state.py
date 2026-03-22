"""
project/state.py
================
Project dataclass — single source of truth for the Streamlit session.

Modules store their results in the named dicts (pvt, volumetrics, etc.).
The outer structure is always plain-Python-serializable. Module results
store quantia objects by calling their .to_dict() before storing.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Project:
    name:              str       = "Unnamed Project"
    scope:             str       = "well"    # "well" | "field"
    units:             str       = "field"   # "field" | "si"
    n_samples:         int       = 3000
    seed:              int | None = 42
    created:           str       = field(default_factory=lambda: str(date.today()))
    version:           str       = "0.1.0"

    # Module result buckets — populated as the user works through pages.
    # Values are plain dicts (quantia objects serialized via .to_dict()).
    pvt:               dict      = field(default_factory=dict)
    volumetrics:       dict      = field(default_factory=dict)
    material_balance:  dict      = field(default_factory=dict)
    dca:               dict      = field(default_factory=dict)
    ipr:               dict      = field(default_factory=dict)
    rta:               dict      = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version":          self.version,
            "name":             self.name,
            "scope":            self.scope,
            "units":            self.units,
            "n_samples":        self.n_samples,
            "seed":             self.seed,
            "created":          self.created,
            "pvt":              self.pvt,
            "volumetrics":      self.volumetrics,
            "material_balance": self.material_balance,
            "dca":              self.dca,
            "ipr":              self.ipr,
            "rta":              self.rta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(
            name             = d.get("name",             "Unnamed Project"),
            scope            = d.get("scope",            "well"),
            units            = d.get("units",            "field"),
            n_samples        = d.get("n_samples",        3000),
            seed             = d.get("seed",             42),
            created          = d.get("created",          str(date.today())),
            version          = d.get("version",          "0.1.0"),
            pvt              = d.get("pvt",              {}),
            volumetrics      = d.get("volumetrics",      {}),
            material_balance = d.get("material_balance", {}),
            dca              = d.get("dca",              {}),
            ipr              = d.get("ipr",              {}),
            rta              = d.get("rta",              {}),
        )

    @property
    def has_pvt(self) -> bool:
        return bool(self.pvt)

    @property
    def has_volumetrics(self) -> bool:
        return bool(self.volumetrics)