import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml
from django.conf import settings

from ctf.models.exceptions import ContainerOperationError

logger = logging.getLogger(__name__)


def get_templates_dir() -> Path:
    """Get the templates directory path"""
    templates_dir = Path(settings.BASE_DIR) / "game-challenges"
    if not templates_dir.exists():
        raise ValueError(f"Templates directory not found: {templates_dir}")
    return templates_dir


def get_compose_path(template_dir: Path) -> Optional[Path]:
    """Get the docker-compose file path"""
    compose_yaml = template_dir / "docker-compose.yaml"
    compose_yml = template_dir / "docker-compose.yml"
    return compose_yaml if compose_yaml.exists() else compose_yml if compose_yml.exists() else None


def read_metadata(template_dir: Path) -> Dict[str, Any]:
    """Read metadata from challenge.yaml"""
    metadata_path = template_dir / "challenge.yaml"
    if metadata_path.exists():
        return yaml.safe_load(metadata_path.read_text())
    return {}


def read_template_info(template_dir: Path) -> Optional[Dict[str, Any]]:
    """Read template information from a directory"""
    try:
        compose_path = get_compose_path(template_dir)
        if not compose_path:
            raise ContainerOperationError(f"No docker-compose file found in {template_dir}")

        compose_content = compose_path.read_text()
        metadata = read_metadata(template_dir)

        return {
            "name": metadata.get("name", template_dir.name),
            "title": metadata.get("title", f"Container template from {template_dir.name}"),
            "description": metadata.get("description", f"Container template from {template_dir.name}"),
            "docker_compose": compose_content,
            "containers": metadata.get("containers", []),
            "networks": metadata.get("networks", [])
        }
    except Exception as e:
        logger.error(f"Error reading template from {template_dir}: {e}")
        return None
