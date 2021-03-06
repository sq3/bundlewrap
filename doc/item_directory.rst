.. _item_directory:

###############
Directory items
###############

.. code-block:: python

    directories = {
        "/path/to/directory": {
            "mode": "0644",
            "owner": "root",
            "group": "root",
        },
    }

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

``group``
+++++++++

Name of the group this directory belongs to. Defaults to ``None`` (don't care about group).

``mode``
++++++++

Directory mode as returned by :command:`stat -c %a <directory>`. Defaults to ``None`` (don't care about mode).

``owner``
+++++++++

Username of the directory's owner. Defaults to ``None`` (don't care about owner).
