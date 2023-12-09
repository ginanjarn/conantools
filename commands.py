"""conan helper"""

import threading
from pathlib import Path

import sublime
import sublime_plugin

from .api import conan


class OutputPanel:
    """"""

    def __init__(self):
        self.panel_name = "conantools"
        self.panel: sublime.View = None

    @property
    def window(self) -> sublime.Window:
        return sublime.active_window()

    def create_panel(self) -> None:
        if self.panel and self.panel.is_valid():
            return

        self.panel = self.window.create_output_panel(self.panel_name)

        settings = {
            "gutter": False,
            "auto_indent": False,
            "word_wrap": False,
        }
        self.panel.settings().update(settings)
        self.panel.set_read_only(False)

    def show(self) -> None:
        """show panel"""
        # ensure panel is created
        self.create_panel()

        self.window.run_command("show_panel", {"panel": f"output.{self.panel_name}"})

    def clear(self) -> None:
        if not self.panel:
            return

        self.panel.run_command("select_all")
        self.panel.run_command("left_delete")

    def write(self, s: str) -> int:
        # ensure panel is created
        self.create_panel()

        self.panel.run_command("insert", {"characters": s})
        return len(s)


def get_workspace_path(view: sublime.View) -> Path:
    """get workspace path
    Use directory contain 'CMakeLists.txt' as workspace path.

    Raise FileNotFoundError if not found.
    """

    file_name = view.file_name()
    folders = [
        folder for folder in view.window().folders() if file_name.startswith(folder)
    ]

    # sort form shortest path
    folders.sort()
    # set first folder contain 'conanfile.py' or 'conanfile.txt' as workspace path
    for folder in folders:
        if (path := Path(folder).joinpath("conanfile.py")) and path.is_file():
            return path.parent

        if (path := Path(folder).joinpath("conanfile.txt")) and path.is_file():
            return path.parent

    raise FileNotFoundError("unable find 'conanfile'")


OUTPUT_PANEL = OutputPanel()


class ConantoolsInstallDependenciesCommand(sublime_plugin.WindowCommand):
    def run(self):
        workspace = get_workspace_path(self.window.active_view())
        thread = threading.Thread(target=self.run_task, args=(workspace,))
        thread.start()

    def run_task(self, workspace):
        settings = sublime.load_settings("Conan.sublime-settings")

        conan_bin = settings.get("conan")
        generator = settings.get("generator")
        build_opt = settings.get("build_option") or "missing"
        build_type = settings.get("build_type") or "Release"
        build_prefix = settings.get("build_prefix") or "build"
        profile = settings.get("profile")

        params = conan.ConanInstallCommand(conan_bin, workspace)
        params.set_build_option(build_opt)
        params.set_generator(generator)
        params.set_settings(build_type=build_type)
        params.set_profile(profile)
        params.set_output_folder(Path(workspace).joinpath(build_prefix))

        OUTPUT_PANEL.show()
        conan.exec_childprocess(params.command(), OUTPUT_PANEL)
