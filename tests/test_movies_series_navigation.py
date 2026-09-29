import ast
from pathlib import Path
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def get_method(filename, class_name, method_name):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)


class MoviesSeriesNavigationTests(unittest.TestCase):
    def test_menu_items_definition(self):
        source = (ROOT / 'lib/nimbus.py').read_text(encoding='utf-8')
        self.assertIn("'Movies'", source)
        self.assertIn("'TV Series'", source)
        self.assertIn("self.menu_items = ('Home', 'Movies', 'TV Series', 'Search', 'Library', 'Addons', 'Settings')", source)

    def test_load_catalog_section_movies(self):
        fn = get_method('lib/nimbus.py', 'HomeWindow', 'load_catalog_section')
        window = Mock()
        window.account_rows = [
            {'label': 'Continue Watching', 'items': [{'id': 'm1', 'type': 'movie'}, {'id': 's1', 'type': 'series'}]},
            {'label': 'Popular Movies', 'kind': 'movie', 'items': [{'id': 'm2', 'type': 'movie'}]},
            {'label': 'Popular Series', 'kind': 'series', 'items': [{'id': 's2', 'type': 'series'}]},
        ]
        window.movie_catalog = None
        window.movie_extras = {}
        window.movie_skip = 0
        window.populate_rows = Mock()
        window.setProperty = Mock()

        scope = {'api': Mock(), 'getattr': getattr, 'setattr': setattr}
        scope['api'].discover_choices.return_value = [{'kind': 'movie', 'label': 'Popular Movies'}]
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<nimbus>', 'exec'), scope)

        scope['load_catalog_section'](window, 'movie')

        window.populate_rows.assert_called_once()
        page, rows = window.populate_rows.call_args[0]
        self.assertEqual(page, 'Movies')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['label'], 'Continue Watching')
        self.assertEqual(len(rows[0]['items']), 1)
        self.assertEqual(rows[0]['items'][0]['id'], 'm1')
        self.assertEqual(rows[1]['label'], 'Popular Movies')

        window.setProperty.assert_any_call('filter_label_0', 'All Movies')

    def test_load_catalog_section_series(self):
        fn = get_method('lib/nimbus.py', 'HomeWindow', 'load_catalog_section')
        window = Mock()
        window.account_rows = [
            {'label': 'Continue Watching', 'items': [{'id': 'm1', 'type': 'movie'}, {'id': 's1', 'type': 'series'}]},
            {'label': 'Popular Movies', 'kind': 'movie', 'items': [{'id': 'm2', 'type': 'movie'}]},
            {'label': 'Popular Series', 'kind': 'series', 'items': [{'id': 's2', 'type': 'series'}]},
        ]
        window.series_catalog = None
        window.series_extras = {}
        window.series_skip = 0
        window.populate_rows = Mock()
        window.setProperty = Mock()

        scope = {'api': Mock(), 'getattr': getattr, 'setattr': setattr}
        scope['api'].discover_choices.return_value = [{'kind': 'series', 'label': 'Popular Series'}]
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<nimbus>', 'exec'), scope)

        scope['load_catalog_section'](window, 'series')

        window.populate_rows.assert_called_once()
        page, rows = window.populate_rows.call_args[0]
        self.assertEqual(page, 'TV Series')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['label'], 'Continue Watching')
        self.assertEqual(len(rows[0]['items']), 1)
        self.assertEqual(rows[0]['items'][0]['id'], 's1')
        self.assertEqual(rows[1]['label'], 'Popular Series')

        window.setProperty.assert_any_call('filter_label_0', 'All TV Series')

    def test_on_action_right_from_sidebar_switches_page(self):
        fn = get_method('lib/nimbus.py', 'HomeWindow', 'onAction')
        window = Mock()
        window.exit_armed = False
        window.getFocusId.return_value = 9000
        window.getProperty.return_value = 'Home'
        window.menu_items = ('Home', 'Movies', 'TV Series', 'Search', 'Library', 'Addons', 'Settings')
        sidebar = Mock()
        sidebar.getSelectedPosition.return_value = 1  # 'Movies'
        window.getControl.return_value = sidebar
        window.onClick = Mock()

        action = Mock()
        action.getId.return_value = 2  # ACTION_MOVE_RIGHT

        scope = {
            'BACK': (10, 92, 216, 247),
            'xbmcgui': Mock(),
            'getattr': getattr,
        }
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<nimbus>', 'exec'), scope)

        scope['onAction'](window, action)
        window.onClick.assert_called_once_with(9000)


if __name__ == '__main__':
    unittest.main()
