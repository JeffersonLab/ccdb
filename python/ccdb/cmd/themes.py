import sys

from .colorama import Fore, Back, Style

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

    def __repr__(self):
        "NoColorTheme"

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

    def __repr__(self):
        "ColoredTheme"


