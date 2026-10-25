"""Tests that MySQL passwords stay out of messages, and that --mysql-pwd puts the password into the connection string"""
import logging
import unittest
from unittest import mock

from sqlalchemy.engine import make_url

from ccdb.cmd import CliManager
from ccdb.provider import hide_password


class HidePasswordTest(unittest.TestCase):

    def test_masks_the_password(self):
        self.assertEqual(hide_password("mysql://ccdb_user:S3cret@hallddb.jlab.org/ccdb"), "mysql://ccdb_user:***@hallddb.jlab.org/ccdb")
        self.assertEqual(hide_password("mysql+pymysql://u:pw@host:3306/db"), "mysql+pymysql://u:***@host:3306/db")

    def test_password_with_an_unescaped_at_sign_is_hidden_whole(self):
        self.assertEqual(hide_password("mysql://bob:p@ss/w#rd@db.example/ccdb"), "mysql://bob:***@db.example/ccdb")

    def test_strings_without_a_password_stay_unchanged(self):
        for text in ["mysql://ccdb_user@hallddb.jlab.org/ccdb", "mysql://hallddb.jlab.org:3306/ccdb",
                     "sqlite:////home/user/ccdb.sqlite", "sqlite:///relative/path:with@signs.sqlite", "not a url"]:
            self.assertEqual(hide_password(text), text)

    def test_masks_the_connection_string_and_password_inside_a_message(self):
        connection_string = "mysql://bob:S3cret@db.example/ccdb"
        message = "Could not parse URL from string '{0}'; login with S3cret failed".format(connection_string)
        masked = hide_password(message, connection_string)
        self.assertNotIn("S3cret", masked)
        self.assertIn("mysql://bob:***@db.example/ccdb", masked)


class MysqlPasswordFlagTest(unittest.TestCase):
    """Runs CliManager.process() with the command execution and the password prompt replaced by mocks"""

    def run_cli(self, *args, password="S3cret"):
        cli = CliManager()
        cli.context.connection_string = "mysql://ccdb_user@localhost/ccdb"
        executed = []
        cli.process_command = lambda command, command_args: executed.append((command, command_args, cli.context.connection_string))
        with mock.patch("ccdb.cmd.cli_manager.getpass.getpass", return_value=password) as prompt:
            cli.process(["ccdb"] + list(args))
        return cli, executed, prompt

    def test_password_goes_into_the_connection_string_given_with_c(self):
        cli, executed, prompt = self.run_cli("--mysql-pwd", "-c", "mysql://bob@db.example/ccdb", "-u", "alice", "ls", "/test")
        prompt.assert_called_once()
        self.assertEqual(executed, [("ls", ["/test"], "mysql://bob:S3cret@db.example/ccdb")])
        self.assertEqual(cli.context.user_name, "alice")

    def test_flag_order_does_not_matter(self):
        for args in (["-c", "mysql://bob@db.example/ccdb", "--mysql-pwd", "-r", "100", "ls"],
                     ["-c", "mysql://bob@db.example/ccdb", "-r", "100", "--mysql-pwd", "ls"]):
            cli, executed, prompt = self.run_cli(*args)
            prompt.assert_called_once()
            self.assertEqual(executed, [("ls", [], "mysql://bob:S3cret@db.example/ccdb")])
            self.assertEqual(cli.context.current_run, 100)

    def test_special_characters_are_escaped(self):
        cli, executed, prompt = self.run_cli("-c", "mysql://bob@db.example/ccdb", "--mysql-pwd", "ls", password="p@ss/w#rd:%")
        url = make_url(executed[0][2])
        self.assertEqual(url.host, "db.example")
        self.assertEqual(url.username, "bob")
        self.assertEqual(url.password, "p@ss/w#rd:%")

    def test_ignored_for_sqlite(self):
        with self.assertLogs("ccdb", level=logging.WARNING):
            cli, executed, prompt = self.run_cli("-c", "sqlite:///ccdb.sqlite", "--mysql-pwd", "ls")
        prompt.assert_not_called()
        self.assertEqual(executed, [("ls", [], "sqlite:///ccdb.sqlite")])

    def test_failed_connect_message_hides_the_password(self):
        cli = CliManager()
        cli.context.connection_string = "mysql://bob:S3cret@db.example/ccdb"
        util = mock.Mock(uses_db=True)
        error = Exception("cannot reach mysql://bob:S3cret@db.example/ccdb")
        with mock.patch.object(cli._prov, "connect", side_effect=error), \
                self.assertLogs("ccdb", level=logging.CRITICAL) as logs:
            self.assertFalse(cli.check_connection(util))
        self.assertNotIn("S3cret", "\n".join(logs.output))
        self.assertIn("mysql://bob:***@db.example/ccdb", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
