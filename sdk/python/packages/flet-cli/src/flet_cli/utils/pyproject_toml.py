from pathlib import Path
from typing import Any, Optional, Sequence, Union

import toml


def load_pyproject_toml(project_dir: Path):
    """Load a pyproject.toml file and returns a function to retrieve configuration values."""
    pyproject_toml: Optional[dict[str, Any]] = {}
    pyproject_toml_file = project_dir.joinpath("pyproject.toml")

    if pyproject_toml_file.exists():
        with pyproject_toml_file.open("r") as f:
            pyproject_toml = toml.loads(f.read())

    def get_pyproject_value(key: str):
        """Retrieve a configuration value from pyproject.toml using a."""
        d = pyproject_toml
        for i in key.split("."):
            d = d.get(i)
            if d is None:
                return None
        return d

    def get_pyproject(keys: Union[str, Sequence[str]], option=None, default=None):
        """
        Retrieve a configuration value from either the CLI option or pyproject.toml settings.

        Parameters:
            *keys (str): One or more keys to look up in pyproject.toml (checked in order).
            option (Any, optional): The value provided by the CLI build/package command. Defaults to None.
            default (Any, optional): The fallback value if no valid setting is found. Defaults to None.

        Returns:
            Any: The first non-None value from `option`, pyproject.toml, or `default`.
        """
        # If CLI option is provided, return it immediately
        if option is not None:
            return option

        # If a single key is provided, convert it to a list
        if isinstance(keys, str):
            keys = [keys]

        # Lookup key in pyproject.toml and return the first non-None value
        for key in keys:
            value = get_pyproject_value(key)
            if value is not None:
                return value

        # Fallback to default value
        return default

    return get_pyproject
