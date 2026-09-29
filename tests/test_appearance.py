from unittest.mock import MagicMock
import unittest
import xml.etree.ElementTree as ET
from lib.appearance import apply, options, NETFLIX_RED
from lib.theme import apply as apply_theme, index, NAMES, PALETTES


class AppearanceTests(unittest.TestCase):
    def test_no_animation_preserves_sidebar_position_rule_and_dims_rows(self):
        tree = ET.ElementTree(ET.fromstring(
            '<window><control id="2000"><animation effect="slide" end="490,0" time="500" condition="Control.HasFocus(9000)">Conditional</animation></control><texture colordiffuse="FFFFFFFF">masks/poster-glow-widget.png</texture></window>'))
        apply(tree, {'color': 'FF55BBFF', 'animations': False, 'dim': True})
        self.assertEqual(tree.find('.//animation').get('time'), '0')
        self.assertEqual(tree.find('.//animation').get('end'), '490,0')
        self.assertEqual(tree.find('.//texture').get('colordiffuse'), 'FF55BBFF')
        self.assertEqual(tree.findall('.//animation')[1].get('end'), '45')

    def test_netflix_theme_palette_and_index(self):
        self.assertIn('Netflix', NAMES)
        netflix_index = NAMES.index('Netflix')
        self.assertEqual(netflix_index, 5)
        self.assertEqual(PALETTES[netflix_index][0], 'FF0E0E0E')  # Dark/pitch background
        self.assertEqual(PALETTES[netflix_index][5], 'FFE50914')  # Netflix Red focus
        self.assertEqual(PALETTES[netflix_index][7], 'FFFFFFFF')  # White text on focus

        addon_num = MagicMock()
        addon_num.getSetting.side_effect = lambda k: '5' if k == 'ui_theme' else ''
        self.assertEqual(index(addon_num), 5)

        addon_str = MagicMock()
        addon_str.getSetting.side_effect = lambda k: 'Netflix' if k == 'ui_theme' else ''
        self.assertEqual(index(addon_str), 5)

    def test_netflix_theme_application(self):
        xml = (
            '<window>'
            '  <control type="image">'
            '    <texture colordiffuse="FF0F1017">bg.png</texture>'
            '  </control>'
            '  <control type="image">'
            '    <texture colordiffuse="FFFFFFFF">masks/poster-glow-widget.png</texture>'
            '  </control>'
            '  <control type="image">'
            '    <texture colordiffuse="FFF0F0F2">masks/flixicon-filled.png</texture>'
            '  </control>'
            '  <control type="label">'
            '    <textcolor>FF15161D</textcolor>'
            '  </control>'
            '  <control id="9000">'
            '    <focusedlayout>'
            '      <control type="label"><textcolor>FFE5E5E5</textcolor></control>'
            '      <control type="image"><texture colordiffuse="FFFFFFFF">bar.png</texture></control>'
            '    </focusedlayout>'
            '  </control>'
            '</window>'
        )
        tree = ET.ElementTree(ET.fromstring(xml))
        apply_theme(tree, selected=5)

        textures = tree.findall('.//texture')
        self.assertEqual(textures[0].get('colordiffuse'), 'FF0E0E0E')
        self.assertEqual(textures[1].get('colordiffuse'), 'FFE50914')
        self.assertEqual(textures[2].get('colordiffuse'), 'FFE50914')
        txt = tree.find('.//textcolor')
        self.assertEqual(txt.text, 'FFFFFFFF')
        sidebar_txt = tree.find('.//control[@id="9000"]/focusedlayout/control/textcolor')
        sidebar_img = tree.find('.//control[@id="9000"]/focusedlayout/control/texture')
        self.assertEqual(sidebar_txt.text, 'FFE50914')
        self.assertEqual(sidebar_img.get('colordiffuse'), 'FFE50914')

    def test_netflix_red_focus_options_and_button_styling(self):
        addon = MagicMock()
        addon.getSetting.side_effect = lambda k: '5' if k == 'ui_theme' else ('5' if k == 'ui_focus_color' else 'true')
        opts = options(addon)
        self.assertEqual(opts['theme'], 5)
        self.assertEqual(opts['color'], NETFLIX_RED)

        addon_custom = MagicMock()
        addon_custom.getSetting.side_effect = lambda k: '1' if k == 'ui_theme' else ('6' if k == 'ui_focus_color' else 'true')
        opts_custom = options(addon_custom)
        self.assertEqual(opts_custom['color'], NETFLIX_RED)

        tree = ET.ElementTree(ET.fromstring(
            '<window>'
            '  <control id="9200"><texturefocus colordiffuse="FFFFFFFF"/></control>'
            '  <control id="9201"><texturefocus colordiffuse="FFFFFFFF"/></control>'
            '  <control id="9202"><texturefocus colordiffuse="FFFFFFFF"/></control>'
            '</window>'
        ))
        apply(tree, {'color': NETFLIX_RED})
        self.assertEqual(tree.find('.//control[@id="9200"]/texturefocus').get('colordiffuse'), NETFLIX_RED)
        self.assertEqual(tree.find('.//control[@id="9201"]/texturefocus').get('colordiffuse'), NETFLIX_RED)
        self.assertEqual(tree.find('.//control[@id="9202"]/texturefocus').get('colordiffuse'), NETFLIX_RED)
