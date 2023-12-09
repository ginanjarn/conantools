import os
import subprocess
import shlex
from pathlib import Path
from typing import List, Optional, Any, Iterator

if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


class StreamWriter:
    """Stream writer interface"""

    def write(self, s: str) -> int:
        raise NotImplementedError


def exec_childprocess(
    command: List[str],
    writer: StreamWriter,
    *,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> int:
    """exec_childprocess, write result to writer object"""

    if isinstance(command, str):
        command = shlex.split(command)

    print(f"execute '{shlex.join(command)}'")

    # ensure if cwd is directory
    if not (cwd and Path(cwd).is_dir()):
        cwd = None

    # update from current environment
    if env:
        environ = os.environ
        env = environ.update(env)
        env = environ

    process = subprocess.Popen(
        command,
        # stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # redirect to stdout
        startupinfo=STARTUPINFO,
        bufsize=0,
        cwd=cwd,
        shell=True,
        env=env,
    )

    while line := process.stdout.readline():
        writer.write(line.rstrip().decode() + "\n")

    return process.poll()


def normalize(commands: List[Any]) -> Iterator[str]:
    """normalize command as str"""
    for command in commands:
        if isinstance(command, Path):
            yield command.as_posix()
        else:
            yield str(command)


class ConanInstallCommand:
    def __init__(self, executable: Path, conanfile_dir: Path):
        self._commands = [
            executable,
            "install",
            conanfile_dir,
        ]

    def command(self) -> List[str]:
        return list(normalize(self._commands))

    def set_build_option(self, build: str):
        """Optional, specify which packages to build from source.

        Combining multiple '--build' options on one command
        line is allowed. Possible values: --build="*" Force
        build from source for all packages. --build=never
        Disallow build for all packages, use binary packages
        or fail if a binary package is not found, it cannot be
        combined with other '--build' options. --build=missing
        Build packages from source whose binary package is not
        found. --build=cascade Build packages from source that
        have at least one dependency being built from source.
        --build=[pattern] Build packages from source whose
        package reference matches the pattern. The pattern
        uses 'fnmatch' style wildcards. --build=~[pattern]
        Excluded packages, which will not be built from the
        source, whose package reference matches the pattern.
        The pattern uses 'fnmatch' style wildcards.
        --build=missing:[pattern] Build from source if a
        compatible binary does not exist, only for packages
        matching pattern.
        """
        if build:
            self._commands.extend(["--build", build])
        return self

    def set_profile(self, profile: str):
        """Apply the specified profile to the host machine"""
        if profile:
            self._commands.extend(["--profile", profile])
        return self

    def set_generator(self, generator: str):
        """Build generator"""
        if generator:
            self._commands.extend(["--generator", generator])
        return self

    def set_output_folder(self, path: Path):
        """The root output folder for generated and build files"""
        if path:
            self._commands.extend(["--output-folder", path])
        return self

    def set_settings(self, mapped_settings: dict = None, **settings):
        """Settings to build the package, overwriting the
        defaults (build machine). e.g.: -s:b compiler=gcc
        """

        def apply(inner_settings: dict):
            if inner_settings:
                for k, v in inner_settings.items():
                    self._commands.extend(["-s", f"{k}={v}"])

        # keyword argument settings
        apply(settings)

        if isinstance(mapped_settings, dict):
            apply(mapped_settings)

        return self

    def set_options(self, mapped_options: dict = None, **options):
        """Define options values (build machine),
        e.g.: -o Pkg:with_qt=true
        """

        def apply(inner_options: dict):
            if inner_options:
                for k, v in inner_options.items():
                    self._commands.extend(["-o", f"{k}={v}"])

        # keyword argument settings
        apply(options)

        if isinstance(mapped_options, dict):
            apply(mapped_options)

        return self
