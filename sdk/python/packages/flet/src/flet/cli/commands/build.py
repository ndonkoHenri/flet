import argparse
from pathlib import Path

from flet.cli.commands.base import BaseCommand
from flet_core.utils import slugify
from rich import print


class Command(BaseCommand):
    """
    Build an executable app or install bundle.
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "output_directory",
            type=str,
            help="output directory",
        )
        parser.add_argument(
            "--project-name",
            dest="project_name",
            help="project name for executable or bundle",
            required=False,
        )
        parser.add_argument(
            "--description",
            dest="description",
            help="the description to use for executable or bundle",
            required=False,
        )

    def handle(self, options: argparse.Namespace) -> None:
        from cookiecutter.main import cookiecutter

        template_name = "flet_build"
        template_data = {"template_name": template_name}

        out_dir = Path(options.output_directory).resolve()
        template_data["out_dir"] = out_dir.name

        project_name = slugify(
            options.project_name if options.project_name else out_dir.name
        )
        template_data["project_name"] = project_name

        if options.description is not None:
            template_data["description"] = options.description

        # check if `flutter` executable is available in the path

        # create Flutter project from a template
        cookiecutter(
            f"gh:flet-dev/flet-app-templates",
            directory=template_name,
            output_dir=str(out_dir.parent),
            no_input=True,
            overwrite_if_exists=True,
            extra_context=template_data,
        )

        # convert icons

        # package Python app

        # run `flutter build`
