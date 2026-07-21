"""Color themes for CLI output.

Themes are plain string constants holding ANSI escape prefixes that commands
concatenate into their output. The escape codes are produced through rich's
color API so color names stay symbolic; see docs/development/cli-modernization.md
for the longer-term plan of moving output to rich Console entirely.
"""

from rich.color import Color

_CSI = "\x1b["


def _ansi(color_name=None, bold=False):
    """ANSI escape prefix for a named color, e.g. _ansi('green', bold=True)"""
    codes = ["1"] if bold else []
    if color_name:
        codes.extend(Color.parse(color_name).get_ansi_codes(foreground=True))
    return _CSI + ";".join(codes) + "m" if codes else ""


class NoColorTheme:
    Ok = ""
    Directories = ""
    HelpCommand = ""
    Registring = ""
    UtilName = ""
    Reset = ""
    Success = ""
    Fail = ""
    Accent = ""
    Title = ""
    Type = ""
    AsgmtHead = ""
    AsgmtType = ""
    AsgmtValue = ""
    AsgmtBorder = ""

    def __repr__(self):
        return "NoColorTheme"


class ColoredTheme(NoColorTheme):
    Ok = _ansi("green", bold=True)
    Directories = _ansi("blue", bold=True)
    HelpCommand = _ansi("blue", bold=True)
    Registring = _ansi("blue")
    UtilName = _ansi("green")
    Reset = _CSI + "0m"
    Success = _ansi("green", bold=True)
    Fail = _ansi("red", bold=True)
    Accent = _ansi("blue", bold=True)
    Title = _ansi(bold=True)
    Type = _ansi("cyan")
    AsgmtHead = _ansi("blue", bold=True)
    AsgmtType = ""
    AsgmtValue = ""
    AsgmtBorder = _ansi("green")

    def __repr__(self):
        return "ColoredTheme"
