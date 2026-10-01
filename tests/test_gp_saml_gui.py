import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import gp_saml_gui as gui


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        html = '<html>SAML form</html>'
        self.session = Mock()
        self.session.headers = {}
        self.session.post.return_value.content = (
            '<prelogin-response><status>Success</status>'
            '<saml-auth-method>POST</saml-auth-method>'
            '<saml-request>{}</saml-request></prelogin-response>'
        ).format(b64encode(html.encode()).decode()).encode()
        self.login = SimpleNamespace(
            closed=False, success=True,
            saml_result={
                'saml-username': 'test@example.org',
                'prelogin-cookie': 'fresh-test-cookie',
                'server': 'vpn.example.org',
            },
        )

    def run_main(self, arguments):
        output = io.StringIO()
        with patch.object(gui.requests, 'Session', return_value=self.session), \
                patch.object(gui, 'SAMLLoginViewWebview', return_value=self.login), \
                patch.object(gui, 'stderr', io.StringIO()), contextlib.redirect_stdout(output):
            gui.main(['--pywebview', 'vpn.example.org'] + arguments)
        return output.getvalue()

    def test_cookie_is_bound_to_the_requested_interface(self):
        for option, interface, endpoint in (
                ('--portal', 'portal', 'global-protect/prelogin.esp'),
                ('--gateway', 'gateway', 'ssl-vpn/prelogin.esp')):
            with self.subTest(interface=interface):
                output = self.run_main([option])
                self.assertIn(
                    'HOST=https://vpn.example.org/{}:prelogin-cookie'.format(interface), output)
                self.assertIn('COOKIE=fresh-test-cookie', output)
                self.assertEqual(self.session.post.call_args[0][0],
                                 'https://vpn.example.org/' + endpoint)

    def test_failed_openconnect_does_not_replay_cookie(self):
        for option, interface in (('--portal', 'portal'), ('--gateway', 'gateway')):
            with self.subTest(interface=interface):
                cookie_input = []

                def capture_stdin(fd, target):
                    self.assertEqual(target, 0)
                    cookie_input.append(os.read(fd, 1024))

                with patch.object(gui, 'dup2', side_effect=capture_stdin), \
                        patch.object(gui, 'execvp', side_effect=SystemExit(1)) as execute:
                    with self.assertRaises(SystemExit) as error:
                        self.run_main([option, '--sudo-openconnect', '--', '--background'])
                self.assertEqual(error.exception.code, 1)
                execute.assert_called_once()
                command = execute.call_args[0][1]
                self.assertEqual(command[:2], ['sudo', 'openconnect'])
                self.assertIn('--usergroup=' + interface + ':prelogin-cookie', command)
                self.assertIn('--background', command)
                self.assertEqual(cookie_input, [b'fresh-test-cookie\n'])


class BrowserDebugTests(unittest.TestCase):
    def test_verbosity_does_not_enable_devtools(self):
        for arguments in ([], ['-v'], ['-v', '-v'], ['-q']):
            with self.subTest(arguments=arguments):
                _, args = gui.parse_args(['vpn.example.org'] + arguments)
                with patch.object(gui, 'webview') as webview:
                    gui.SAMLLoginViewWebview(None, '<html></html>', args)
                self.assertIs(webview.start.call_args[1]['debug'], False)

    def test_devtools_can_be_enabled_explicitly(self):
        _, args = gui.parse_args(['vpn.example.org', '-q', '--debug'])
        with patch.object(gui, 'webview') as webview:
            gui.SAMLLoginViewWebview(None, '<html></html>', args)
        self.assertIs(webview.start.call_args[1]['debug'], True)


class UniTNLauncherTests(unittest.TestCase):
    def test_start_requests_a_gateway_cookie_without_devtools(self):
        # Exercise the shell launcher without opening a login window or VPN.
        launcher = Path(__file__).resolve().parents[1] / 'bin' / 'gp-saml-gui-unitn'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bin').mkdir()
            python = root / '.direnv' / 'test' / 'bin' / 'python3'
            python.parent.mkdir(parents=True)
            python.write_text(
                '#!/bin/sh\n'
                'printf "%s\\n" "$@" > "$GP_TEST_ARGUMENTS"\n'
                'printf "%s\\n" "$$" > "$GP_TEST_PID_FILE"\n')
            python.chmod(0o755)
            hip = root / 'hipreport.sh'
            hip.write_text('#!/bin/sh\nexit 0\n')
            hip.chmod(0o755)
            script = root / 'bin' / launcher.name
            script.write_text(launcher.read_text().replace(
                '/opt/homebrew/opt/openconnect/libexec/openconnect/hipreport.sh', str(hip)))
            captured = root / 'arguments'
            result = subprocess.run(
                ['bash', str(script), 'start'], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                env=dict(os.environ, GP_TEST_ARGUMENTS=str(captured),
                         GP_TEST_PID_FILE=str(root / 'gp-saml-gui.pid')),
                timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            _, args = gui.parse_args(captured.read_text().splitlines()[1:])
            self.assertEqual(args.server, 'vpn-mfa.icts.unitn.it')
            self.assertEqual(args.interface, 'gateway')
            self.assertEqual(args.exec, 'sudo')
            self.assertFalse(args.debug)
            self.assertIn('--background', args.openconnect_extra)


if __name__ == '__main__':
    unittest.main()
