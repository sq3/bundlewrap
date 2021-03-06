# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.text import bold, green, red
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("systemctl start -- {}".format(quote(svcname)))


def svc_running(node, svcname):
    result = node.run(
        "systemctl status -- {}".format(quote(svcname)),
        may_fail=True,
    )
    if result.return_code != 0:
        return False
    else:
        return True


def svc_stop(node, svcname):
    return node.run("systemctl stop -- {}".format(quote(svcname)))


class SvcSystemd(Item):
    """
    A service managed by systemd.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_systemd"
    ITEM_ATTRIBUTES = {
        'running': True,
    }
    ITEM_TYPE_NAME = "svc_systemd"
    NEEDS_STATIC = [
        "pkg_apt:",
        "pkg_dnf",
        "pkg_pacman:",
        "pkg_yum:",
        "pkg_zypper:",
        "pkg_pkgsrc:",
    ]

    def __repr__(self):
        return "<SvcSystemd name:{} running:{}>".format(
            self.name,
            self.attributes['running'],
        )

    def ask(self, status):
        before = _("running") if status.info['running'] \
            else _("not running")
        after = green(_("running")) if self.attributes['running'] \
            else red(_("not running"))
        return "{} {} → {}\n".format(
            bold(_("status")),
            before,
            after,
        )

    def fix(self, status):
        if self.attributes['running'] is False:
            LOG.info(_("{node}:{bundle}:{item}: stopping...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            svc_stop(self.node, self.name)
        else:
            LOG.info(_("{node}:{bundle}:{item}: starting...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            svc_start(self.node, self.name)

    def get_canned_actions(self):
        return {
            'reload': {
                'command': "systemctl reload -- {}".format(self.name),
                'needs': [self.id],
            },
            'restart': {
                'command': "systemctl restart -- {}".format(self.name),
                'needs': [self.id],
            },
        }

    def get_status(self):
        service_running = svc_running(self.node, self.name)
        item_status = (service_running == self.attributes['running'])
        return ItemStatus(
            correct=item_status,
            info={'running': service_running},
        )

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('running', True), bool):
            raise BundleError(_(
                "expected boolean for 'running' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
