class BraceMessage(object):
    """
    This class is used for logger formatting via new string format
    example:
    from ccdb import BraceMessage as lfm
    ...
    log.debug(lfm("Format this {0}", 3.14))

    Full description could be found here
    http://docs.python.org/3/howto/logging-cookbook.html#use-of-alternative-formatting-styles
    """

    def __init__(self, fmt, *args, **kwargs):
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return self.fmt.format(*self.args, **self.kwargs)
