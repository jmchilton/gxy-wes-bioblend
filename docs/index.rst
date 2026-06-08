gxy-wes-bioblend
================

**gxy-wes-bioblend** is a Galaxy `GA4GH Workflow Execution Service (WES)`_
client and command line tool built on `BioBlend`_'s client layer. BioBlend does
not implement the WES endpoints, but it does provide the rest: API-key storage,
request/retry plumbing, and abstractions for uploading datasets, creating
histories, and reading job logs. This project adds only the WES wire protocol on
top of a BioBlend :class:`~bioblend.galaxy.GalaxyInstance`.

It is the BioBlend-based sibling of the dependency-light `gxy-wes`_ project,
which speaks WES with a hand-rolled ``requests`` wrapper instead.

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   :hidden:

   Overview <readme>
   Installation <installation>
   Usage <usage>
   CLI <cli>

.. toctree::
   :maxdepth: 2
   :caption: Development
   :hidden:

   Developing <developing>

Quick start
-----------

.. code-block:: console

   $ uvx gxy-wes-bioblend service-info --galaxy-url http://localhost:8080
   $ export GXY_WES_API_KEY=...
   $ uvx gxy-wes-bioblend demo --galaxy-url http://localhost:8080

See :doc:`installation` and :doc:`usage` to get going, and :doc:`cli` for the
full command reference.

.. _Galaxy: https://galaxyproject.org
.. _GA4GH Workflow Execution Service (WES): https://ga4gh.github.io/workflow-execution-service-schemas/
.. _BioBlend: https://bioblend.readthedocs.io/
.. _gxy-wes: https://github.com/jmchilton/gxy-wes
