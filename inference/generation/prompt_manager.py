"""Load versioned prompt templates from YAML and render with Jinja2."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template

logger = logging.getLogger(__name__)


class PromptTemplate:
    """A single loaded + renderable prompt template."""

    def __init__(self, name: str, version: str, raw_template: str, variables: list[str]):
        self.name = name
        self.version = version
        self.raw_template = raw_template
        self.variables = variables
        self._jinja = Template(raw_template)
        self.hash = hashlib.sha256(raw_template.encode()).hexdigest()[:12]

    def render(self, **kwargs: Any) -> str:
        return self._jinja.render(**kwargs)

    @property
    def metadata(self) -> dict:
        return {
            "prompt_name": self.name,
            "prompt_version": self.version,
            "prompt_hash": self.hash,
        }


class PromptManager:
    """Manages versioned prompt templates from the prompts/ directory."""

    def __init__(self, prompts_dir: str | Path = "prompts", version: str = "v1"):
        self._base = Path(prompts_dir)
        self._version = version
        self._cache: dict[str, PromptTemplate] = {}

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        v = version or self._version
        cache_key = f"{v}/{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._base / v / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")

        data = yaml.safe_load(path.read_text())
        template = PromptTemplate(
            name=data.get("name", name),
            version=data.get("version", v),
            raw_template=data["template"],
            variables=data.get("variables", []),
        )
        self._cache[cache_key] = template
        logger.info("Loaded prompt %s/%s (hash=%s)", v, name, template.hash)
        return template

    def render(self, name: str, *, version: str | None = None, **kwargs: Any) -> str:
        template = self.get(name, version)
        return template.render(**kwargs)

    def get_metadata(self, name: str, version: str | None = None) -> dict:
        template = self.get(name, version)
        return template.metadata
