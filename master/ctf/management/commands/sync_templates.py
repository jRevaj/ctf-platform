import logging
from pathlib import Path
from typing import Optional

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand

from ctf.models import ChallengeTemplate
from ctf.models.exceptions import ContainerOperationError

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync container templates from filesystem with database"

    def handle(self, *args, **options):
        logger.info("Syncing container templates...")

        try:
            templates_dir = self.get_templates_dir()
            template_dirs = [d for d in templates_dir.iterdir() if d.is_dir()]

            processed_templates = self._process_templates(template_dirs)
            removed_count = self._cleanup_obsolete_templates(processed_templates)

            if removed_count:
                logger.warning(f"Removed {removed_count} obsolete templates")

            logger.info("Template sync completed!")
        except ContainerOperationError as e:
            logger.error(f"Template operation failed: {e}")
        except Exception as e:
            logger.error(f"Error syncing templates: {e}")

    @staticmethod
    def get_templates_dir() -> Path:
        templates_dir = Path(settings.BASE_DIR) / "game-challenges"
        if not templates_dir.exists():
            raise ValueError(f"Templates directory not found: {templates_dir}")
        return templates_dir

    def read_template_info(self, template_dir: Path) -> Optional[dict]:
        """Read template information from a directory"""
        try:
            compose_path = self._get_compose_path(template_dir)
            if not compose_path:
                raise ContainerOperationError(f"No docker-compose file found in {template_dir}")

            compose_content = compose_path.read_text()
            metadata = self._read_metadata(template_dir)

            return {"name": metadata.get("name", template_dir.name),
                    "title": metadata.get("title", f"Container template from {template_dir.name}"),
                    "description": metadata.get("description", f"Container template from {template_dir.name}"),
                    "docker_compose": compose_content,
                    "containers": metadata.get("containers", []),
                    "networks": metadata.get("networks", [])}
        except Exception as e:
            logger.error(f"Error reading template from {template_dir}: {e}")
            return None

    @staticmethod
    def _get_compose_path(template_dir: Path) -> Path:
        """Get the docker-compose file path"""
        compose_yaml = template_dir / "docker-compose.yaml"
        compose_yml = template_dir / "docker-compose.yml"

        return compose_yaml if compose_yaml.exists() else compose_yml if compose_yml.exists() else None

    @staticmethod
    def _read_metadata(template_dir: Path) -> dict:
        """Read metadata from challenge.yaml"""
        metadata_path = template_dir / "challenge.yaml"
        if metadata_path.exists():
            return yaml.safe_load(metadata_path.read_text())
        return {}

    def _process_templates(self, template_dirs) -> set:
        """Process all challenge directories"""
        processed_templates = set()

        for template_dir in template_dirs:
            template_info = self.read_template_info(template_dir)
            if not template_info:
                continue

            template, created = ChallengeTemplate.objects.update_or_create(
                name=template_info["name"],
                defaults={
                    "folder": template_dir.name,
                    "name": template_info["name"],
                    "title": template_info["title"] if "title" in template_info else None,
                    "description": template_info["description"] if "description" in template_info else None,
                    "docker_compose": template_info["docker_compose"] if "docker_compose" in template_info else None,
                    "containers_config": template_info["containers"] if "containers" in template_info else None,
                    "networks_config": template_info["networks"] if "networks" in template_info else None
                },
            )

            action = "Created" if created else "Updated"
            logger.info(f"{action} template: {template.name}")

            processed_templates.add(template.name)

        return processed_templates

    @staticmethod
    def _cleanup_obsolete_templates(processed_templates: set) -> int:
        """Remove templates that no longer exist in filesystem"""
        return ChallengeTemplate.objects.exclude(name__in=processed_templates).delete()[0]
