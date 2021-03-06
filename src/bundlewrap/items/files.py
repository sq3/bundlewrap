# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from datetime import datetime
from os import remove
from os.path import basename, dirname, exists, join, normpath
from pipes import quote
from subprocess import call
from sys import exc_info
from tempfile import mkstemp
from traceback import format_exception

from bundlewrap.exceptions import BundleError, TemplateError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.items.directories import validator_mode
from bundlewrap.utils import cached_property, hash_local_file, sha1
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import force_text, mark_for_translation as _
from bundlewrap.utils.text import is_subdirectory
from bundlewrap.utils.ui import io


DIFF_MAX_FILE_SIZE = 1024 * 1024 * 5  # bytes
DIFF_MAX_LINE_LENGTH = 128


def content_processor_jinja2(item):
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        raise TemplateError(_(
            "Unable to load Jinja2 (required to render {item}). "
            "You probably have to install it using `pip install Jinja2`."
        ).format(item=item.id))

    loader = FileSystemLoader(searchpath=[item.item_data_dir, item.item_dir])
    env = Environment(loader=loader)

    template = env.from_string(item._template_content)

    io.debug("{node}:{bundle}:{item}: rendering with Jinja2...".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
    ))
    start = datetime.now()
    try:
        content = template.render(
            item=item,
            bundle=item.bundle,
            node=item.node,
            repo=item.node.repo,
            **item.attributes['context']
        )
    except Exception as e:
        io.debug("".join(format_exception(*exc_info())))
        raise TemplateError(_(
            "Error while rendering template for {node}:{bundle}:{item}: {error}"
        ).format(
            bundle=item.bundle.name,
            error=e,
            item=item.id,
            node=item.node.name,
        ))
    duration = datetime.now() - start
    io.debug("{node}:{bundle}:{item}: rendered in {time}s".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
        time=duration.total_seconds(),
    ))
    return content.encode(item.attributes['encoding'])


def content_processor_mako(item):
    from mako.lookup import TemplateLookup
    from mako.template import Template
    template = Template(
        item._template_content.encode('utf-8'),
        input_encoding='utf-8',
        lookup=TemplateLookup(directories=[item.item_data_dir, item.item_dir]),
        output_encoding=item.attributes['encoding'],
    )
    io.debug("{node}:{bundle}:{item}: rendering with Mako...".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
    ))
    start = datetime.now()
    try:
        content = template.render(
            item=item,
            bundle=item.bundle,
            node=item.node,
            repo=item.node.repo,
            **item.attributes['context']
        )
    except Exception as e:
        io.debug("".join(format_exception(*exc_info())))
        if isinstance(e, NameError) and e.message == "Undefined":
            # Mako isn't very verbose here. Try to give a more useful
            # error message - even though we can't pinpoint the excat
            # location of the error. :/
            e = _("Undefined variable (look for '${...}')")
        raise TemplateError(_(
            "Error while rendering template for {node}:{bundle}:{item}: {error}"
        ).format(
            bundle=item.bundle.name,
            error=e,
            item=item.id,
            node=item.node.name,
        ))
    duration = datetime.now() - start
    io.debug("{node}:{bundle}:{item}: rendered in {time}s".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
        time=duration.total_seconds(),
    ))
    return content


def content_processor_text(item):
    return item._template_content.encode(item.attributes['encoding'])


CONTENT_PROCESSORS = {
    'any': lambda item: "",
    'binary': None,
    'jinja2': content_processor_jinja2,
    'mako': content_processor_mako,
    'text': content_processor_text,
}


def get_remote_file_contents(node, path):
    """
    Returns the contents of the given path as a string.
    """
    handle, tmp_file = mkstemp()
    node.download(path, tmp_file)
    with open(tmp_file) as f:
        content = f.read()
    remove(tmp_file)
    return content


def validator_content_type(item_id, value):
    if value not in CONTENT_PROCESSORS:
        raise BundleError(_(
            "invalid content_type for {item}: '{value}'"
        ).format(item=item_id, value=value))


ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)
ATTRIBUTE_VALIDATORS.update({
    'content_type': validator_content_type,
    'mode': validator_mode,
})


class File(Item):
    """
    A file.
    """
    BUNDLE_ATTRIBUTE_NAME = "files"
    ITEM_ATTRIBUTES = {
        'content': None,
        'content_type': 'text',
        'context': None,
        'delete': False,
        'encoding': "utf-8",
        'group': None,
        'mode': None,
        'owner': None,
        'source': None,
        'verify_with': None,
    }
    ITEM_TYPE_NAME = "file"
    NEEDS_STATIC = ["user:"]

    def __repr__(self):
        return "<File path:{} content_hash:{}>".format(
            quote(self.name),
            self.content_hash,
        )

    @property
    def _template_content(self):
        if self.attributes['source'] is not None:
            filename = join(self.item_data_dir, self.attributes['source'])
            if exists(filename):
                with open(filename) as f:
                    content = f.read()
            else:
                filename = join(self.item_dir, self.attributes['source'])
                with open(filename) as f:
                    content = f.read()
            return force_text(content)
        else:
            return force_text(self.attributes['content'])

    @cached_property
    def content(self):
        return CONTENT_PROCESSORS[self.attributes['content_type']](self)

    @cached_property
    def content_hash(self):
        if self.attributes['content_type'] == 'binary':
            return hash_local_file(self.template)
        else:
            return sha1(self.content)

    @cached_property
    def template(self):
        data_template = join(self.item_data_dir, self.attributes['source'])
        if exists(data_template):
            return data_template
        return join(self.item_dir, self.attributes['source'])

    def cdict(self):
        if self.attributes['delete']:
            return {}
        cdict = {'type': 'file'}
        if self.attributes['content_type'] != 'any':
            cdict['content_hash'] = self.content_hash
        for optional_attr in ('group', 'mode', 'owner'):
            if self.attributes[optional_attr] is not None:
                cdict[optional_attr] = self.attributes[optional_attr]
        return cdict

    def fix(self, status):
        for fix_type in ('type', 'content', 'mode', 'owner', 'group'):
            if fix_type in status.info['needs_fixing']:
                if fix_type == 'group' and \
                        'owner' in status.info['needs_fixing']:
                    # owner and group are fixed with a single chown
                    continue
                if fix_type in ('mode', 'owner', 'group') and \
                        'content' in status.info['needs_fixing']:
                    # fixing content implies settings mode and owner/group
                    continue
                if status.info['path_info'].exists:
                    if self.attributes['delete']:
                        io.stdout(_("{node}:{bundle}:{item}: deleting...").format(
                            bundle=self.bundle.name, node=self.node.name, item=self.id))
                    else:
                        io.stdout(_("{node}:{bundle}:{item}: fixing {type}...").format(
                            bundle=self.bundle.name,
                            item=self.id,
                            node=self.node.name,
                            type=fix_type,
                        ))
                else:
                    io.stdout(_("{node}:{bundle}:{item}: creating...").format(
                        bundle=self.bundle.name, item=self.id, node=self.node.name))
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_content(self, status):
        local_path = self._write_local_file()

        try:
            self.node.upload(
                local_path,
                self.name,
                mode=self.attributes['mode'],
                owner=self.attributes['owner'] or "",
                group=self.attributes['group'] or "",
            )
        finally:
            if self.attributes['content_type'] != 'binary':
                remove(local_path)

    def _fix_mode(self, status):
        self.node.run("chmod {} -- {}".format(
            self.attributes['mode'],
            quote(self.name),
        ))

    def _fix_owner(self, status):
        group = self.attributes['group'] or ""
        if group:
            group = ":" + quote(group)
        self.node.run("chown {}{} -- {}".format(
            quote(self.attributes['owner'] or ""),
            group,
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        if status.info['path_info'].exists:
            self.node.run("rm -rf -- {}".format(quote(self.name)))
        if not self.attributes['delete']:
            self.node.run("mkdir -p -- {}".format(quote(dirname(self.name))))
            self._fix_content(status)

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item.ITEM_TYPE_NAME == "file" and is_subdirectory(item.name, self.name):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') blocking path to "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
            elif item.ITEM_TYPE_NAME in ("directory", "symlink"):
                if is_subdirectory(item.name, self.name):
                    deps.append(item.id)
        return deps

    def sdict(self):
        path_info = PathInfo(self.node, self.name)
        if not path_info.exists:
            return {}
        else:
            return {
                'type': path_info.path_type,
                'content_hash': path_info.sha1 if path_info.path_type == 'file' else None,
                'mode': path_info.mode,
                'owner': path_info.owner,
                'group': path_info.group,
                'size': path_info.size,
            }

    def patch_attributes(self, attributes):
        if 'content' not in attributes and 'source' not in attributes:
            attributes['source'] = basename(self.name)
        if 'context' not in attributes:
            attributes['context'] = {}
        if 'mode' in attributes and attributes['mode'] is not None:
            attributes['mode'] = str(attributes['mode']).zfill(4)
        return attributes

    def test(self):
        if self.attributes['source'] and not exists(self.template):
            raise BundleError(_(
                "{item} from bundle '{bundle}' refers to missing "
                "file '{path}' in its 'source' attribute"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
                path=self.template,
            ))

        local_path = self._write_local_file()
        if self.attributes['content_type'] != 'binary':
            remove(local_path)

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('delete', False):
            for attr in attributes.keys():
                if attr not in ['delete'] + list(BUILTIN_ITEM_ATTRIBUTES.keys()):
                    raise BundleError(_(
                        "{item} from bundle '{bundle}' cannot have other "
                        "attributes besides 'delete'"
                    ).format(item=item_id, bundle=bundle.name))
        if 'content' in attributes and 'source' in attributes:
            raise BundleError(_(
                "{item} from bundle '{bundle}' cannot have both 'content' and 'source'"
            ).format(item=item_id, bundle=bundle.name))

        if (
            attributes.get('content_type', None) == "any" and (
                'content' in attributes or
                'encoding' in attributes or
                'source' in attributes
            )
        ):
            raise BundleError(_(
                "{item} from bundle '{bundle}' with content_type 'any' "
                "must not define 'content', 'encoding' and/or 'source'"
            ).format(item=item_id, bundle=bundle.name))

        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](item_id, value)

    @classmethod
    def validate_name(cls, bundle, name):
        if normpath(name) == "/":
            raise BundleError(_("'/' cannot be a file"))
        if normpath(name) != name:
            raise BundleError(_(
                "'{path}' is an invalid file path, should be '{normpath}' (bundle '{bundle}')"
            ).format(
                bundle=bundle.name,
                normpath=normpath(name),
                path=name,
            ))

    def _write_local_file(self):
        """
        Makes the file contents available at the returned temporary path
        and performs local verification if necessary or requested.

        The calling method is responsible for cleaning up the file at
        the returned path (only if not a binary).
        """
        if self.attributes['content_type'] == 'binary':
            local_path = self.template
        else:
            handle, local_path = mkstemp()
            with open(local_path, 'wb') as f:
                f.write(self.content)

        if self.attributes['verify_with']:
            cmd = self.attributes['verify_with'].format(quote(local_path))
            io.debug("calling local verify command for {i}: {c}".format(c=cmd, i=self.id))
            if call(cmd, shell=True) == 0:
                io.debug("{i} passed local validation".format(i=self.id))
            else:
                raise BundleError(_(
                    "{i} failed local validation using: {c}"
                ).format(c=cmd, i=self.id))

        return local_path
