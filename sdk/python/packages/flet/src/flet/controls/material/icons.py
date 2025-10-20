"""
Flet Material Icons

To generate/update this file run from the root of the repository:

```
uv run .github/scripts/generate_icons.py
```
"""

from flet.controls.icon_data import IconData

__all__ = ["Icons"]


class Icons(IconData, package_name="flet", class_name="Icons"):
    ABC = 0x10000
    ABC_OUTLINED = 0x10001
    ABC_ROUNDED = 0x10002
    ABC_SHARP = 0x10003
    AC_UNIT = 0x10004
    
