"""GPU-free contract tests: python3 -B -m unittest discover -s tests -v."""

from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HELPER = Path(__file__).resolve().parents[1] / "scripts" / "pip_packages.py"
spec = importlib.util.spec_from_file_location("pip_packages", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

IDENTITY = {
    "schema": 1,
    "python": ["cpython", "3.14.4", "cpython-314-x86_64-linux-gnu"],
    "platform": ["linux", "x86_64", "ubuntu", "26.04"],
    "libc": ["glibc", "2.43"],
}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "runtime.json"
        self.manifest.write_text(json.dumps({"schema": 1, "dependency_generation": "a" * 64}))
        self.cache = self.root / "cache"
        self.identity = copy.deepcopy(IDENTITY)
        self.identity_mock = patch.object(helper, "runtime_identity", side_effect=lambda: self.identity).start()
        self.addCleanup(patch.stopall)
        self.pip = patch.object(helper.subprocess, "run", return_value=SimpleNamespace(returncode=0)).start()
        patch.dict(os.environ, {"PIP_NO_CACHE_DIR": "1", "PIP_INDEX_URL": "https://secret@example.invalid"}).start()
        self.output = io.StringIO()

    def install(self, value=None):
        with redirect_stdout(self.output):
            return helper.install_packages(value, manifest=self.manifest, cache_root=self.cache)

    def command(self):
        return self.pip.call_args.args[0]

    def test_unset_empty_whitespace(self):
        with patch.dict(os.environ, {}, clear=True):
            for value in (None, "", " \t\n "):
                with self.subTest(value=value):
                    self.assertEqual(self.install(value), 0)
        self.pip.assert_not_called()
        self.identity_mock.assert_not_called()
        self.assertFalse(self.cache.exists())

    def test_first_start_scoped_cache_and_same_interpreter(self):
        self.assertEqual(self.install("example==1.0"), 0)
        command = self.command()
        self.assertEqual(command[:5], [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"])
        self.assertEqual(command[-1], "example==1.0")
        self.assertEqual(command[-3], "--cache-dir")
        cache = Path(command[-2])
        self.assertTrue(cache.is_dir())
        self.assertEqual(cache.stat().st_mode & 0o077, 0)
        self.assertEqual(cache.parent, self.cache / "v1")
        self.assertRegex(cache.name, r"^[a-f0-9]{64}$")
        self.assertNotIn("PIP_NO_CACHE_DIR", self.pip.call_args.kwargs["env"])
        self.assertEqual(os.environ["PIP_NO_CACHE_DIR"], "1")
        self.assertEqual(self.pip.call_args.kwargs["env"]["PIP_INDEX_URL"], os.environ["PIP_INDEX_URL"])
        self.assertNotIn("shell", self.pip.call_args.kwargs)
        self.assertNotIn("cwd", self.pip.call_args.kwargs)

    def test_restart_and_recreation_always_invoke_pip(self):
        # Reusing only the manifest/cache is all a recreated container can rely
        # on. Neither previous success nor any persistent marker may skip pip.
        for event in ("first", "restart", "recreation"):
            with self.subTest(event=event):
                self.assertEqual(self.install("example==1.0"), 0)
        self.assertEqual(self.pip.call_count, 3)
        commands = [call.args[0] for call in self.pip.call_args_list]
        self.assertEqual(commands, [commands[0]] * 3)
        self.assertEqual(list(self.cache.rglob("*.json")), [])

    def test_changes_pins_and_removal_do_not_uninstall(self):
        for value in ("one==1 two", "one==2 two three", "one==2", ""):
            self.install(value)
        self.assertEqual(self.pip.call_count, 3)
        for call, expected in zip(self.pip.call_args_list,
                                  (["one==1", "two"], ["one==2", "two", "three"], ["one==2"])):
            self.assertEqual(call.args[0][7:], expected)
            self.assertNotIn("uninstall", call.args[0])

    def test_explicit_options_remain_last(self):
        for option in ("--no-cache-dir", "--upgrade", "--force-reinstall",
                       "--cache-dir /custom/cache", "--cache-dir=/custom/cache"):
            with self.subTest(option=option):
                self.install("example " + option)
                self.assertEqual(self.command()[7:], ["example", *helper.shlex.split(option)])

    def test_requirements_urls_editables_and_shell_text_are_literal(self):
        arguments = [
            "pkg[extra]>=1", "-r", "requirements with spaces.txt", "-c", "constraints.txt",
            "name @ https://user:token@example.invalid/pkg.whl",
            "git+https://example.invalid/repo.git@main#egg=name", "-e", "./local project",
            "$(touch /tmp/should-not-exist)", "`id`", "$TOKEN", "*.whl", ";",
        ]
        self.install(helper.shlex.join(arguments))
        self.assertEqual(self.command()[7:], arguments)
        self.assertNotIn("token", self.output.getvalue())
        self.assertNotIn("https://", self.output.getvalue())

    def test_runtime_changes_separate_paths(self):
        self.install("example")
        original = self.command()[6]
        changes = {
            "schema": 2,
            "python": ["cpython", "3.15", "new-soabi"],
            "platform": ["linux", "aarch64", "ubuntu", "26.04"],
            "libc": ["glibc", "2.44"],
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                self.identity = copy.deepcopy(IDENTITY)
                self.identity[field] = value
                self.install("example")
                self.assertNotEqual(self.command()[6], original)

    def test_image_generation_changes_path(self):
        self.install("example")
        original = self.command()[6]
        self.manifest.write_text(json.dumps({"schema": 1, "dependency_generation": "b" * 64}))
        self.install("example")
        self.assertNotEqual(self.command()[6], original)

    def test_requests_credentials_and_build_settings_do_not_change_path(self):
        self.install("one")
        original = self.command()[6]
        with patch.dict(os.environ, {"PIP_PACKAGES": "two", "PIP_INDEX_URL": "https://new-secret.invalid"}):
            self.install()
            self.assertEqual(self.command()[6], original)
        with patch.dict(os.environ, {"TORCH_XPU_ARCH_LIST": "pvc"}):
            self.install("one")
            self.assertEqual(self.command()[6], original)

    def test_missing_manifest_falls_back(self):
        self.manifest.unlink()
        self.assertEqual(self.install("example"), 0)
        self.assertEqual(self.command()[5:], ["--no-cache-dir", "example"])
        self.assertFalse(self.cache.exists())

    def test_corrupt_manifest_falls_back(self):
        for content in ("{broken", "null", "[]", "{}", '{"schema":2}',
                        '{"schema":1,"dependency_generation":"../../private"}'):
            with self.subTest(content=content):
                self.manifest.write_text(content)
                self.assertEqual(self.install("example"), 0)
                self.assertEqual(self.command()[5:], ["--no-cache-dir", "example"])

    def test_unavailable_identity_falls_back_without_exception_details(self):
        self.identity_mock.side_effect = RuntimeError("private-token")
        self.assertEqual(self.install("example"), 0)
        self.assertIn("--no-cache-dir", self.command())
        self.assertNotIn("private-token", self.output.getvalue())

    def test_unwritable_cache_falls_back(self):
        with patch.object(helper.tempfile, "TemporaryFile", side_effect=PermissionError):
            self.assertEqual(self.install("example"), 0)
        self.assertIn("--no-cache-dir", self.command())
        self.assertIn("cache unavailable", self.output.getvalue())

    def test_cache_path_is_file_falls_back(self):
        self.cache.write_text("not a directory")
        self.assertEqual(self.install("example"), 0)
        self.assertIn("--no-cache-dir", self.command())

    def test_pip_failure_and_retry(self):
        self.pip.return_value.returncode = 23
        self.assertEqual(self.install("https://user:secret@example.invalid/pkg.whl"), 23)
        self.assertNotIn("secret", self.output.getvalue())
        self.assertNotIn("processed", self.output.getvalue())
        self.pip.return_value.returncode = 0
        self.assertEqual(self.install("example"), 0)
        self.assertEqual(self.pip.call_count, 2)

    def test_pip_signal_and_launch_failure(self):
        self.pip.return_value.returncode = -9
        self.assertEqual(self.install("example"), 1)
        self.pip.side_effect = OSError("secret")
        self.assertEqual(self.install("example"), 1)
        self.assertNotIn("secret", self.output.getvalue())

    def test_invalid_quoting_stops_without_echo(self):
        self.assertEqual(self.install('"private-token'), 1)
        self.pip.assert_not_called()
        self.assertNotIn("private-token", self.output.getvalue())


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.distributions = [SimpleNamespace(
            metadata={"Name": name}, version="1.0",
            read_text=lambda filename: "record contents",
        ) for name in sorted(helper.REQUIRED_DISTRIBUTIONS)]
        self.distribution_scan = patch.object(helper.metadata, "distributions", return_value=self.distributions).start()
        self.system_scan = patch.object(helper.subprocess, "run", return_value=SimpleNamespace(
            stdout="libze1\t1.0\tamd64\tinstalled\nlibc6\t2.43\tamd64\tinstalled\n")).start()
        self.addCleanup(patch.stopall)

    def test_collected_identity_includes_builds_and_is_order_independent(self):
        first = helper.base_dependency_identity()
        self.distributions.reverse()
        self.assertEqual(first, helper.base_dependency_identity())
        self.assertEqual({item[0] for item in first["distributions"]}, helper.REQUIRED_DISTRIBUTIONS)
        self.assertTrue(first["python"][2])
        self.assertEqual(first["distributions"][0][2], helper.digest("record contents"))

    def test_missing_required_distribution_or_record_is_rejected(self):
        self.distributions[0].read_text = lambda filename: None
        with self.assertRaises(ValueError):
            helper.base_dependency_identity()
        self.distributions.pop(0)
        with self.assertRaises(ValueError):
            helper.base_dependency_identity()

    def test_user_package_install_upgrade_downgrade_and_removal_keep_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            checksum = Path(directory) / "libc.md5sums"
            checksum.write_text("base-native-package-checksums")
            with patch.object(Path, "glob", return_value=[checksum]):
                helper.write_manifest(path)
            manifest_contents = path.read_text()
            before = helper.runtime_key(path)
            self.distribution_scan.reset_mock()
            self.system_scan.reset_mock()
            user_package = SimpleNamespace(metadata={"Name": "user-package"}, version="1.0",
                                           read_text=lambda filename: "user RECORD")
            self.distributions.append(user_package)
            self.assertEqual(before, helper.runtime_key(path), "installation changed key")
            for version in ("2.0", "0.9"):
                user_package.version = version
                user_package.read_text = lambda filename: "changed user RECORD"
                self.assertEqual(before, helper.runtime_key(path), "upgrade/downgrade changed key")
            self.distributions.remove(user_package)
            self.assertEqual(before, helper.runtime_key(path), "removal changed key")
            # Even replacing/removing packages originally supplied by the image
            # must not recalculate the authoritative base dependency digest.
            for package in self.distributions:
                package.version = "user-replacement"
                package.read_text = lambda filename: None
            self.assertEqual(before, helper.runtime_key(path))
            self.distributions.clear()
            self.assertEqual(before, helper.runtime_key(path))
            self.distribution_scan.assert_not_called()
            self.system_scan.assert_not_called()
            self.assertEqual(manifest_contents, path.read_text())

    def test_stable_runtime_facts_change_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({"schema": 1, "dependency_generation": "a" * 64}))
            before = helper.runtime_key(path)
            for target, attribute, value in (
                (helper.sys, "version", "different-python-version"),
                (helper.sys, "platform", "different-platform"),
            ):
                with self.subTest(attribute=attribute), patch.object(target, attribute, value):
                    self.assertNotEqual(before, helper.runtime_key(path))
            for target, attribute, value in (
                (helper.sysconfig, "get_config_var", "different-soabi"),
                (helper.platform, "machine", "different-architecture"),
                (helper.platform, "libc_ver", ("glibc", "different-version")),
            ):
                with self.subTest(attribute=attribute), patch.object(target, attribute, return_value=value):
                    self.assertNotEqual(before, helper.runtime_key(path))

    def test_changed_base_python_dependencies_change_generated_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            checksum = Path(directory) / "libc.md5sums"
            checksum.write_text("native-package-checksums")
            with patch.object(Path, "glob", return_value=[checksum]):
                helper.write_manifest(path)
                before = helper.runtime_key(path)
                self.distributions[0].read_text = lambda filename: "new base wheel build"
                helper.write_manifest(path)
                self.assertNotEqual(before, helper.runtime_key(path))

    def test_generation_is_deterministic_and_contains_no_user_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            checksum = Path(directory) / "libc.md5sums"
            checksum.write_text("native-package-content-hashes")
            with patch.object(Path, "glob", return_value=[checksum]), patch.dict(os.environ, {
                "PIP_PACKAGES": "private-request", "PIP_INDEX_URL": "private-token",
            }):
                helper.write_manifest(path)
                first = path.read_text()
                helper.write_manifest(path)
                self.assertEqual(first, path.read_text())
                self.assertEqual(set(json.loads(first)), {"schema", "dependency_generation"})
                self.assertNotIn("private", first)
                checksum.write_text("changed-native-package-content-hashes")
                helper.write_manifest(path)
                self.assertNotEqual(first, path.read_text())

    def test_unavailable_build_identity_writes_disabled_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            with patch.object(Path, "glob", return_value=[]), redirect_stdout(io.StringIO()):
                helper.write_manifest(path)
            self.assertIsNone(json.loads(path.read_text())["dependency_generation"])
            with self.assertRaises(ValueError):
                helper.runtime_key(path)


class HelperProcessTests(unittest.TestCase):
    def test_restart_and_same_image_recreation_keep_key_in_fresh_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            recreated = root / "recreated"
            original.mkdir()
            recreated.mkdir()
            manifest = json.dumps({"schema": 1, "dependency_generation": "a" * 64})
            for container in (original, recreated):
                (container / "runtime.json").write_text(manifest)
            launcher = (
                "import importlib.util, pathlib, sys; "
                "s=importlib.util.spec_from_file_location('helper', sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "print(m.runtime_key(pathlib.Path('runtime.json')))"
            )
            keys = []
            for event, container, request in (
                ("first startup", original, "one==1"),
                ("restart", original, "one==2 two"),
                ("recreation", recreated, "three"),
            ):
                with self.subTest(event=event):
                    result = subprocess.run(
                        [sys.executable, "-B", "-c", launcher, str(HELPER)],
                        cwd=container, env={**os.environ, "PIP_PACKAGES": request},
                        capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    keys.append(result.stdout.strip())
            self.assertRegex(keys[0], r"^[a-f0-9]{64}$")
            self.assertEqual(keys, [keys[0]] * 3)

    def test_real_child_process_preserves_arguments_environment_and_failure(self):
        # Run the real helper and Python -m boundary. This stub never installs
        # anything; real pip/cache integration still requires a pip environment.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pip.py").write_text(
                "import json, os, sys\n"
                "print('PIP_STUB=' + json.dumps({'args': sys.argv[1:], "
                "'cache_disabled_env': 'PIP_NO_CACHE_DIR' in os.environ}))\n"
                "sys.exit(int(os.environ['TEST_PIP_EXIT']))\n"
            )
            arguments = ["-r", "requirements file.txt", "--force-reinstall",
                         "$(touch should-not-exist)", "git+https://example.invalid/repo.git"]
            env = {**os.environ, "PYTHONPATH": directory, "PYTHONDONTWRITEBYTECODE": "1",
                   "PIP_PACKAGES": helper.shlex.join(arguments), "PIP_NO_CACHE_DIR": "1"}
            # Supply an explicit missing manifest so this test is independent
            # of whether it is run inside the full application image.
            launcher = (
                "import importlib.util, pathlib, sys; "
                "s=importlib.util.spec_from_file_location('helper', sys.argv[1]); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "sys.exit(m.install_packages(manifest=pathlib.Path('missing.json')))"
            )
            for exit_code in (0, 17):
                with self.subTest(exit_code=exit_code):
                    result = subprocess.run(
                        [sys.executable, "-B", "-c", launcher, str(HELPER)],
                        cwd=root, env={**env, "TEST_PIP_EXIT": str(exit_code)},
                        capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, exit_code, result.stderr)
                    line = next(line for line in result.stdout.splitlines() if line.startswith("PIP_STUB="))
                    report = json.loads(line.removeprefix("PIP_STUB="))
                    self.assertEqual(report["args"], ["install", "--disable-pip-version-check",
                                                      "--no-cache-dir", *arguments])
                    self.assertFalse(report["cache_disabled_env"])
                    self.assertFalse((root / "should-not-exist").exists())

    def test_cli_empty_value_does_not_launch_pip(self):
        result = subprocess.run(
            [sys.executable, "-B", str(HELPER)],
            env={**os.environ, "PIP_PACKAGES": " \t\n"},
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[INFO] No additional Python packages requested.")


class EntrypointTests(unittest.TestCase):
    def test_failure_stops_before_manager_and_request_is_not_echoed(self):
        # Execute the actual package section with a fake Python executable.
        # This tests bash's set -e boundary without running Manager or ComfyUI.
        source = (HELPER.parents[1] / "entrypoint.sh").read_text()
        section = source.split("# Optional user-installed Python packages", 1)[1]
        section = section.split("# Optional ComfyUI CLI arguments", 1)[0]
        result = subprocess.run(
            ["bash", "-c", "set -e\npython() { return 19; }\n" + section + '\necho SHOULD_NOT_LAUNCH'],
            capture_output=True, text=True,
            env={**os.environ, "PIP_PACKAGES": "private-token"},
        )
        self.assertEqual(result.returncode, 19)
        self.assertNotIn("SHOULD_NOT_LAUNCH", result.stdout)
        self.assertNotIn("private-token", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
