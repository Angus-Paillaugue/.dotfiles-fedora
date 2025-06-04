import gi
import setproctitle

gi.require_version("GLib", "2.0")
from fabric.utils import get_relative_path, monitor_file
from fabric import Application
from modules.bar import Bar
from modules.launcher import AppLauncher
import services.config as config

if __name__ == "__main__":
    setproctitle.setproctitle(config.APP_NAME)
    bar = Bar()
    launcher = AppLauncher()
    app = Application(config.APP_NAME, bar, launcher)
    def apply_stylesheet(*_):
        return app.set_stylesheet_from_file(get_relative_path("main.css"))

    # Load main stylesheet
    style_monitor = monitor_file(get_relative_path("main.css"))
    style_monitor.connect("changed", apply_stylesheet)
    apply_stylesheet()
    app.run()

