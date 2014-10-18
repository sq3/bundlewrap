from unittest import TestCase

from mock import MagicMock

from bundlewrap.cmdline import verify


class FakeNode(object):
    name = "nodename"

    def verify(self, workers=4):
        return ()


class ApplyTest(TestCase):
    """
    Tests bundlewrap.cmdline.verify.bw_verify.
    """
    def test_interactive(self):
        node1 = FakeNode()
        repo = MagicMock()
        repo.get_node.return_value = node1
        args = {}
        args['item_workers'] = 4
        args['target'] = "node1"
        verify.bw_verify(repo, args)
