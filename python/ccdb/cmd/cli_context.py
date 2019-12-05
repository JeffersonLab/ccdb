import posixpath


class CliContext(object):
    anonymous_user_name = "anonymous"

    def __init__(self, provider, theme, commands):
        self._prov = provider
        self.theme = theme
        self._commands = commands

        self.is_interactive = False
        self.current_path = "/"
        self.current_run = 0
        self.current_variation = "default"
        self.connection_string = ""

        if self._prov:
            self.user_name = self.anonymous_user_name

    @property
    def provider(self):
        return self._prov

    @property
    def user_name(self):
        return self._prov.authentication.current_user_name

    @user_name.setter
    def user_name(self, name):
        self._prov.authentication.current_user_name = name

    @property
    def commands(self):
        return self._commands

    # --------------------------------
    #  prepare_path
    # --------------------------------
    def prepare_path(self, path):

        # correct ending /
        if path.endswith("/"):
            path = path[:-1]

        # local or absolute path?
        if not path.startswith("/"):
            path = posixpath.join(self.current_path, path)
            # normalize
        path = posixpath.normpath(path)

        return path
