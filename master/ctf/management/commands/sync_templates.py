import logging

from django.core.management.base import BaseCommand

from ctf.models import ChallengeTemplate
from ctf.models.exceptions import ContainerOperationError
from ctf.utils.template_helpers import get_templates_dir, read_template_info

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync container templates from filesystem with database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Sync all templates located in /game-challenges",
        )
        parser.add_argument(
            "template_names",
            nargs="*",
            help="Names of specific templates to sync (ignored if --all is used)",
        )

    def handle(self, *args, **options):
        logger.info("Syncing container templates...")

        try:
            templates_dir = get_templates_dir()

            if options["all"]:
                template_dirs = [d for d in templates_dir.iterdir() if d.is_dir()]
            else:
                template_names = options["template_names"]
                if not template_names:
                    logger.error(
                        "No template names provided. Use --all to sync all templates or provide specific template names.")
                    return

                template_dirs = []
                for name in template_names:
                    template_path = templates_dir / name
                    if not template_path.exists():
                        logger.warning(f"Template directory not found: {name}")
                        continue
                    if not template_path.is_dir():
                        logger.warning(f"Not a directory: {name}")
                        continue
                    template_dirs.append(template_path)

            if not template_dirs:
                logger.warning("No valid template directories found to sync.")
                return

            processed_templates = self._process_templates(template_dirs)

            if options["all"]:
                removed_count = self._cleanup_obsolete_templates(processed_templates)
                if removed_count:
                    logger.warning(f"Removed {removed_count} obsolete templates")

            logger.info("Template sync completed!")
        except ContainerOperationError as e:
            logger.error(f"Template operation failed: {e}")
        except Exception as e:
            logger.error(f"Error syncing templates: {e}")

    @staticmethod
    def _process_templates(template_dirs) -> set:
        """Process all challenge directories"""
        processed_templates = set()

        for template_dir in template_dirs:
            template_info = read_template_info(template_dir)
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
