import logging
from pathlib import Path
from typing import Optional

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand

from ctf.models import ContainerTemplate
from ctf.models.exceptions import ContainerOperationError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync container templates from filesystem with database"

    def handle(self, *args, **options):
        self.stdout.write("Syncing container templates...")

        try:
            templates_dir = self._get_templates_dir()
            template_dirs = [d for d in templates_dir.iterdir() if d.is_dir()]

            processed_templates = self._process_templates(template_dirs)
            removed_count = self._cleanup_obsolete_templates(processed_templates)

            if removed_count:
                self.stdout.write(self.style.WARNING(f"Removed {removed_count} obsolete templates"))

            self.stdout.write(self.style.SUCCESS("Template sync completed!"))

        except ContainerOperationError as e:
            self.stderr.write(self.style.ERROR(f"Template operation failed: {e}"))
        except Exception as e:
            logger.exception("Unexpected error in sync_templates")
            self.stderr.write(self.style.ERROR(f"Error syncing templates: {e}"))

    @staticmethod
    def _get_templates_dir() -> Path:
        templates_dir = Path(settings.BASE_DIR) / "container-templates"
        if not templates_dir.exists():
            raise ValueError(f"Templates directory not found: {templates_dir}")
        return templates_dir

    def _read_template_info(self, template_dir: Path) -> Optional[dict]:
        """Read template information from a directory"""
        try:
            compose_path = self._get_compose_path(template_dir)
            if not compose_path:
                raise ContainerOperationError(f"No docker-compose file found in {template_dir}")

            compose_content = compose_path.read_text()
            metadata = self._read_metadata(template_dir)

            return {"name": metadata.get("name", template_dir.name),
                    "description": metadata.get("description", f"Container template from {template_dir.name}"),
                    "docker_compose": compose_content}
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
        """Read metadata from template.yaml"""
        metadata_path = template_dir / "template.yaml"
        if metadata_path.exists():
            return yaml.safe_load(metadata_path.read_text())
        return {}

    def _process_templates(self, template_dirs) -> set:
        """Process all template directories"""
        processed_templates = set()

        for template_dir in template_dirs:
            template_info = self._read_template_info(template_dir)
            if not template_info:
                continue

            template, created = ContainerTemplate.objects.update_or_create(
                name=template_info["name"],
                defaults={
                    "folder": template_dir.name,
                    "description": template_info["description"],
                    "docker_compose": template_info["docker_compose"],
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} template: {template.name}"))

            processed_templates.add(template.name)

        return processed_templates

    @staticmethod
    def _cleanup_obsolete_templates(processed_templates: set) -> int:
        """Remove templates that no longer exist in filesystem"""
        return ContainerTemplate.objects.exclude(name__in=processed_templates).delete()[0]
