import sublime
import sublime_plugin

import os


class SelectColorSchemeCommand(sublime_plugin.WindowCommand):

    PREFS_FILE = 'Preferences.sublime-settings'
    DEFAULT_CS = 'Packages/Color Scheme - Default/Monokai.tmTheme'

    # A list of info about active views in the current window that have
    # view-specific color scheme. This ensures the preview process is at
    # least previewing the color scheme for things the user can see.
    views = None

    # A list of strings containing the package-relative file path of
    # every available color scheme
    schemes = None

    # A sublime.Settings object of the global Sublime Text settings
    prefs = None

    # The last selected row index - used to debounce the search so we
    # aren't apply a new color scheme with every keypress
    last_selected = -1

    def run(self):
        self.prefs = sublime.load_settings(self.PREFS_FILE)

        self.views = None

        self.current = self.prefs.get('color_scheme', self.DEFAULT_CS)

        hidden = self.prefs.get("hidden_color_scheme_pattern") or []

        initial_highlight = -1
        self.schemes = []
        names = []
        package_set = set()

        for cs in sublime.find_resources('*.tmTheme'):
            # Hide certain color schemes from the list
            if any(h in cs for h in hidden):
                continue
            parts = cs.split('/')
            if len(parts) < 3:  # Not in a package
                continue
            pkg = parts[1] if parts[0] == 'Packages' else parts[0]
            name, _ = os.path.splitext(parts[-1])
            names.append(["🎨 " + name, pkg])
            package_set.add(pkg)
            self.schemes.append(cs)

        # special section for compatibility with SublimeLinter
        try:
            initial_highlight = self.schemes.index(self.current)
        except ValueError:
            try:
                # find the original color scheme for a sublimelinter hacked
                original_cs = self.current.replace(" (SL)", "")
                original_cs = os.path.basename(original_cs)
                original_cs = sublime.find_resources(original_cs)[-1]
                initial_highlight = self.schemes.index(original_cs)
            except ValueError:
                initial_highlight = -1

        # Don't show the package name if all color schemes are in the same
        # package
        if len(package_set) == 1:
            names = [name for name, pkg in names]

        self.window.show_quick_panel(
            names,
            self.on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST,
            initial_highlight,
            self.on_highlighted
        )

    def on_done(self, index):
        """
        :param index:
            Integer of the selected quick panel item
        """

        # Reset view-specific color schemes whether a new global
        # color scheme was selected or not
        for settings, original in self.overridden_views(find=False):
            settings.set('color_scheme', original)

        if index == -1:
            self.prefs.set('color_scheme', self.current)
        else:
            self.prefs.set('color_scheme', self.schemes[index])
        sublime.save_settings(self.PREFS_FILE)

    def on_highlighted(self, index):
        """
        :param index:
            Integer of the selected quick panel item
        """

        if index == -1:
            return

        self.last_selected = index

        def update_cs():
            # The selected row has been updated since
            # the timeout was created
            if index != self.last_selected:
                return
            selected = self.schemes[index]
            if self.prefs.get('color_scheme') == selected:
                return
            self.prefs.set('color_scheme', selected)
            for settings, _ in self.overridden_views():
                settings.set('color_scheme', selected)
        sublime.set_timeout(update_cs, 250)

    def overridden_views(self, find=True):
        """
        :param find:
            A bool that controls if the list of views with overridden
            color scheme should be determined, if not already present

        :return:
            A list of dict objects containing the keys:
             - "settings": a sublime.Settings object for the view
             - "original": a string of the original "color_scheme" setting for the view
        """

        if self.views is None:
            vs = set()
            if find is False:
                return vs
            # If the color scheme hasn't been changed, we won't
            # be able to detect overrides
            if self.prefs.get('color_scheme') == self.current:
                return vs
            for i in range(self.window.num_groups()):
                v = self.window.active_view_in_group(i)
                cs = v.settings().get('color_scheme', self.DEFAULT_CS)
                if self.is_view_specific(v):
                    vs.add((v.settings(), cs))
            self.views = vs
        return self.views

    def is_view_specific(self, view):
        """
        :param view:
            A sublime.View object

        :return:
            A bool if the color_scheme is specific to the view
        """

        vcs = view.settings().get('color_scheme', self.DEFAULT_CS)
        pd = self.window.project_data()
        pcs = None
        if pd is not None:
            pcs = pd.get('settings', {}).get('color_scheme')
        gcs = self.prefs.get('color_scheme')

        if pcs is not None and vcs != pcs:
            return True
        return vcs != gcs


class SelectThemeCommand(sublime_plugin.WindowCommand):

    PREFS_FILE = 'Preferences.sublime-settings'
    DEFAULT_THEME = 'Default.sublime-theme'

    # A string of the current theme filename
    current = None

    # A list of strings containing theme filenames
    themes = None

    # A sublime.Settings object of the global Sublime Text settings
    prefs = None

    # The last selected row index - used to debounce the search so we
    # aren't apply a new theme with every keypress
    last_selected = -1

    def run(self):
        self.prefs = sublime.load_settings(self.PREFS_FILE)

        self.current = self.prefs.get('theme', self.DEFAULT_THEME)

        hidden = self.prefs.get("hidden_themes_pattern") or []

        initial_highlight = -1
        self.themes = []
        names = []

        for theme in sublime.find_resources('*.sublime-theme'):
            # Hide certain themes from the list
            if any(h in theme for h in hidden):
                continue

            parts = theme.split('/')
            name = parts[-1]

            # Themes with the same name, but in different packages, are
            # considered a single logical theme, as the data from the
            # different files is merged. Ensure there's only one entry per
            # basename
            if name in self.themes:
                continue
            if name == self.current:
                initial_highlight = len(self.themes)
            if len(parts) < 3:  # Not in a package
                continue
            self.themes.append(name)
            pkg = parts[1] if parts[0] == 'Packages' else parts[0]
            name, _ = os.path.splitext(name)
            names.append(["🖌 " + name, pkg])

        self.window.show_quick_panel(
            names,
            self.on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST,
            initial_highlight,
            self.on_highlighted
        )

    def on_done(self, index):
        """
        :param index:
            Integer of the selected quick panel item
        """

        if index == -1:
            theme = self.current
        else:
            theme = self.themes[index]
        self.prefs.set('theme', theme)
        sublime.save_settings(self.PREFS_FILE)

    def on_highlighted(self, index):
        """
        :param index:
            Integer of the selected quick panel item
        """

        if index == -1:
            return

        self.last_selected = index

        def update_theme():
            # The selected row has been updated since
            # the timeout was created
            if index != self.last_selected:
                return
            self.prefs.set('theme', self.themes[index])
        sublime.set_timeout(update_theme, 250)
