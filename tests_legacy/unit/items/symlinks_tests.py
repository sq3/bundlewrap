# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import call, MagicMock, patch
except ImportError:
    from mock import call, MagicMock, patch

from bundlewrap.exceptions import BundleError
from bundlewrap.items import symlinks, ItemStatus


class SymlinkFixTest(TestCase):
    """
    Tests bundlewrap.items.symlinks.Symlink.fix.
    """
    @patch('bundlewrap.items.symlinks.Symlink._fix_owner')
    @patch('bundlewrap.items.symlinks.Symlink._fix_type')
    def test_type(self, fix_type, fix_owner):
        f = symlinks.Symlink(MagicMock(), "/foo", {'target': "/bar"})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['type', 'owner'],
        })
        f.fix(status)
        fix_type.assert_called_once_with(status)

    @patch('bundlewrap.items.symlinks.Symlink._fix_owner')
    @patch('bundlewrap.items.symlinks.Symlink._fix_type')
    def test_owner(self, fix_type, fix_owner):
        f = symlinks.Symlink(MagicMock(), "/foo", {'target': "/bar"})
        status = ItemStatus(correct=False, info={
            'needs_fixing': ['owner'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)


class SymlinkFixOwnerTest(TestCase):
    """
    Tests bundlewrap.items.symlinks.Symlink._fix_owner.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = symlinks.Symlink(
            bundle,
            "/foo",
            {'owner': "jcleese", 'group': "mp", 'target': "/bar"},
        )
        f._fix_owner(MagicMock())
        node.run.assert_called_once_with("chown -h jcleese:mp -- /foo")


class SymlinkFixTypeTest(TestCase):
    """
    Tests bundlewrap.items.symlinks.Symlink._fix_type.
    """
    @patch('bundlewrap.items.symlinks.Symlink._fix_owner')
    def test_rm(self, fix_owner):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = symlinks.Symlink(
            bundle,
            "/foo",
            {
                'owner': "bw",
                'target': "/bar",
            },
        )
        f._fix_type(MagicMock())
        assert call("rm -rf -- /foo") in node.run.call_args_list
        assert call("ln -s -- /bar /foo") in node.run.call_args_list
        assert fix_owner.call_count == 1


class SymlinkGetAutoDepsTest(TestCase):
    """
    Tests bundlewrap.items.symlinks.Symlink.get_auto_deps.
    """
    def test_file_collision(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "file"
        item1.id = "file:/foo/bar/baz"
        item1.name = "/foo/bar/baz"

        s = symlinks.Symlink(MagicMock(), "/foo/bar/baz", {'target': "/404"})

        items = [item1, s]

        with self.assertRaises(BundleError):
            s.get_auto_deps(items)

    def test_file_parent(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "file"
        item1.id = "file:/foo/bar"
        item1.name = "/foo/bar"

        s = symlinks.Symlink(MagicMock(), "/foo/bar/baz", {'target': "/404"})

        items = [item1, s]

        with self.assertRaises(BundleError):
            s.get_auto_deps(items)

    def test_subdir(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "directory"
        item1.id = "directory:/foo/bar"
        item1.name = "/foo/bar"
        item2 = MagicMock()
        item2.ITEM_TYPE_NAME = "directory"
        item2.id = "directory:/bar/foo"
        item2.name = "/bar/foo"
        item3 = MagicMock()
        item3.ITEM_TYPE_NAME = "file"
        item3.id = "file:/foo/baz"
        item3.name = "/foo/baz"

        s = symlinks.Symlink(MagicMock(), "/foo/bar/baz", {'target': "/404"})

        items = [item1, item2, item3, s]

        self.assertEqual(s.get_auto_deps(items), ["directory:/foo/bar"])

    def test_symlink(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "symlink"
        item1.id = "symlink:/foo/bar"
        item1.name = "/foo/bar"
        item2 = MagicMock()
        item2.ITEM_TYPE_NAME = "directory"
        item2.id = "directory:/bar/foo"
        item2.name = "/bar/foo"
        item3 = MagicMock()
        item3.ITEM_TYPE_NAME = "file"
        item3.id = "file:/foo/baz"
        item3.name = "/foo/baz"

        s = symlinks.Symlink(MagicMock(), "/foo/bar/baz", {'target': "/404"})

        items = [item1, item2, item3, s]

        self.assertEqual(s.get_auto_deps(items), ["symlink:/foo/bar"])


class SymlinkGetStatusTest(TestCase):
    """
    Tests bundlewrap.items.symlinks.Symlink.get_status.
    """
    @patch('bundlewrap.items.symlinks.PathInfo')
    def test_owner(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "jdoe"
        path_info.group = "root"
        path_info.is_symlink = True
        path_info.symlink_target = "/bar"
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/foo", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('bundlewrap.items.symlinks.PathInfo')
    def test_group(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "yolocrowd"
        path_info.is_symlink = True
        path_info.symlink_target = "/bar"
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/foo", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['group'])

    @patch('bundlewrap.items.symlinks.PathInfo')
    def test_target(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_symlink = True
        path_info.symlink_target = "/baz"
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/foo", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['target'])

    @patch('bundlewrap.items.symlinks.PathInfo')
    def test_type(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_symlink = False
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/foo", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['type']),
        )

    @patch('bundlewrap.items.symlinks.PathInfo')
    def test_ok(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.is_symlink = True
        path_info.symlink_target = "/bar"
        PathInfo.return_value = path_info

        f = symlinks.Symlink(MagicMock(), "/foo", {
            'owner': "root",
            'group': "root",
            'target': "/bar",
        })
        status = f.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['needs_fixing'], [])


class ValidateAttributesTest(TestCase):
    """
    Tests bundlewrap.items.symlinks.Symlink.validate_attributes.
    """
    def test_validator_call(self):
        validator = MagicMock()
        attr_val = {
            'attr1': validator,
            'attr2': validator,
        }
        with patch('bundlewrap.items.symlinks.ATTRIBUTE_VALIDATORS', new=attr_val):
            symlinks.Symlink.validate_attributes(
                MagicMock(),
                "symlink:/foo",
                {'attr1': 1, 'attr2': 2},
            )
        validator.assert_any_call("symlink:/foo", 1)
        validator.assert_any_call("symlink:/foo", 2)
        self.assertEqual(validator.call_count, 2)
