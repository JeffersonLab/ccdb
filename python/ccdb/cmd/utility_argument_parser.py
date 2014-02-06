import argparse


class ArgumentParseError(Exception):
    """Error with ccdb.cmd.utility arguments parsing"""
    pass


class UtilityArgumentParser(argparse.ArgumentParser):
    """Throws argument errors instead of exiting application"""

    def error(self, message):
        raise ArgumentParseError(message)

