"""
project/io.py
=============
Save and load Project objects to/from JSON.
"""
from __future__ import annotations
import json
from pathlib import Path
from project.state import Project


def save_project(project: Project, path: str | Path) -> None:
    """Serialize the project to a JSON file."""
    Path(path).write_text(
        json.dumps(project.to_dict(), indent=2), encoding="utf-8"
    )


def load_project(path: str | Path) -> Project:
    """Load a project from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Project.from_dict(data)