import sys

from .colorama import Fore, Back, Style

def bool_color(value):
    if value:
        return Theme.Success
    else:
        return Theme.Fail

def print_bool(value):
    if value:
        sys.stdout.write(Theme.Success + repr(value) + Theme.Reset)
    else:
        sys.stdout.write(Theme.Fail + repr(value) + Theme.Reset)


Theme = None

def set_theme(theme):
    global Theme
    Theme = theme


class NoColorTheme(object):
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

class ColoredTheme(NoColorTheme):
    Ok = Fore.GREEN + Style.BRIGHT
    Directories = Fore.BLUE + Style.BRIGHT
    HelpCommand = Fore.BLUE + Style.BRIGHT
    Registring = Fore.BLUE
    UtilName = Fore.GREEN
    Reset = Style.RESET_ALL
    Success = Fore.GREEN + Style.BRIGHT
    Fail = Fore.RED + Style.BRIGHT
    Accent = Fore.BLUE + Style.BRIGHT
    Title = Style.BRIGHT
    Type = Fore.CYAN
    AsgmtHead = Fore.BLUE + Style.BRIGHT
    AsgmtType = ""
    AsgmtValue = "" 
    AsgmtBorder = Fore.GREEN


