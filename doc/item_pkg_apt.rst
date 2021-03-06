.. _item_pkg_apt:

#################
APT package items
#################

Handles packages installed by ``apt-get`` on Debian-based systems.

.. code-block:: python

    pkg_apt = {
        "foopkg": {
            "installed": True,  # default
        },
        "bar": {
            "installed": False,
        },
    }

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``installed``
+++++++++++++

``True`` when the package is expected to be present on the system; ``False`` if it should be purged.
