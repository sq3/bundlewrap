# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from bundlewrap.cmdline import debug


class DebugTest(TestCase):
    """
    Tests bundlewrap.cmdline.debug.bw_debug.
    """
    @patch('bundlewrap.cmdline.debug.interact')
    def test_interactive(self, interact):
        args = {}
        args['command'] = None
        args['node'] = None
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        with patch(
                'bundlewrap.cmdline.debug.Repository',
                return_value=repo_obj_validated,
        ) as repo_class:
            debug.bw_debug(repo_obj, args)

            repo_class.assert_called_with(repo_obj.path)
            interact.assert_called_with(
                debug.DEBUG_BANNER,
                local={'repo': repo_obj_validated},
            )

    @patch('bundlewrap.cmdline.debug.interact')
    def test_interactive_node(self, interact):
        args = {}
        args['node'] = "node1"
        args['command'] = None
        args['itemid'] = None
        node = MagicMock()
        node.name = args['node']
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        repo_obj_validated.get_node = MagicMock(return_value=node)
        with patch(
                'bundlewrap.cmdline.debug.Repository',
                return_value=repo_obj_validated,
        ):
            debug.bw_debug(repo_obj, args)
            interact.assert_called_with(
                debug.DEBUG_BANNER_NODE,
                local={
                    'node': node,
                    'repo': repo_obj_validated,
                },
            )
