.. image:: https://raw.githubusercontent.com/gosmart-health/tinydb-safe/master/artwork/logo.png
    :height: 150px

|Build Status| |Coverage| |Version|

Quick Links
***********

- `Installation`_
- `Example Code`_
- `Supported Python Versions`_
- `Project Status & Attribution`_
- `Documentation <http://tinydb.readthedocs.org/>`_
- `Changelog <https://tinydb.readthedocs.io/en/latest/changelog.html>`_
- `Extensions <https://tinydb.readthedocs.io/en/latest/extensions.html>`_
- `Contributing`_

Introduction
************

TinyDB is a lightweight document oriented database optimized for your happiness :)
It's written in pure Python and has no external dependencies. The target are
small apps that would be blown away by a SQL-DB or an external database server.

TinyDB-Safe is:

- **tiny:** The current source code has ~1800 lines of code (with about 40%
  documentation) and 1600 lines tests.

- **document oriented:** Like MongoDB_, you can store any document
  (represented as ``dict``) in TinyDB.

- **optimized for your happiness:** TinyDB is designed to be simple and
  fun to use by providing a simple and clean API.

- **written in pure Python:** TinyDB neither needs an external server (as
  e.g. `PyMongo <https://pymongo.readthedocs.io/en/stable/>`_) nor any dependencies
  from PyPI.

- **works on Python 3.11+ and PyPy3:** TinyDB works on all modern versions of Python
  and PyPy.

- **powerfully extensible:** You can easily extend TinyDB by writing new
  storages or modify the behaviour of storages with Middlewares.

- **thread-safe:** Built-in thread safety across storages, tables, and caches
  makes this project safe to use in multi-threaded web applications and frameworks
  like Flask without any changes to API usage from original TinyDB.

- **100% test coverage:** No explanation needed.

To dive straight into all the details, head over to the `TinyDB docs
<https://tinydb.readthedocs.io/>`_. You can also discuss everything related
to TinyDB like general development, extensions or showcase your TinyDB-based
projects on the `discussion forum <http://forum.m-siemens.de/.>`_.

Installation
************

Install TinyDB-Safe using pip:

.. code-block:: bash

    $ pip install tinydb-safe

TinyDB-Safe is a 100% drop-in replacement for TinyDB. In your Python code,
imports remain unchanged:

.. code-block:: python

    from tinydb import TinyDB, Query

Supported Python Versions
*************************

TinyDB has been tested with Python 3.11 - 3.14 and PyPy3.

Project Status & Attribution
****************************

This project (`TinyDB-Safe <https://github.com/gosmart-health/tinydb-safe>`_) is a
thread-safe fork of the original `TinyDB <https://github.com/msiemens/tinydb>`_
created and maintained by `Markus Siemens <https://github.com/msiemens>`_.

The original TinyDB is in `maintenance mode <https://github.com/msiemens/tinydb/discussions/572>`_
as its functionality has reached a mature, stable state where significant new architectural
changes are not planned. TinyDB-Safe was created to add thread safety across tables, storages,
and query caches while maintaining 100% drop-in API compatibility with the original project.

Bugfixes and community contributions continue to be actively welcomed.

Example Code
************

.. code-block:: python

    >>> from tinydb import TinyDB, Query
    >>> db = TinyDB('/path/to/db.json')
    >>> db.insert({'int': 1, 'char': 'a'})
    >>> db.insert({'int': 1, 'char': 'b'})

Query Language
==============

.. code-block:: python

    >>> User = Query()
    >>> # Search for a field value
    >>> db.search(User.name == 'John')
    [{'name': 'John', 'age': 22}, {'name': 'John', 'age': 37}]\

    >>> # Combine two queries with logical and
    >>> db.search((User.name == 'John') & (User.age <= 30))\
    [{'name': 'John', 'age': 22}]

    >>> # Combine two queries with logical or
    >>> db.search((User.name == 'John') | (User.name == 'Bob'))
    [{'name': 'John', 'age': 22}, {'name': 'John', 'age': 37}, {'name': 'Bob', 'age': 42}]

    >>> # Negate a query with logical not
    >>> db.search(~(User.name == 'John'))
    [{'name': 'Megan', 'age': 27}, {'name': 'Bob', 'age': 42}]

    >>> # Apply transformation to field with `map`
    >>> db.search((User.age.map(lambda x: x + x) == 44))
    >>> [{'name': 'John', 'age': 22}]

    >>> # More possible comparisons:  !=  <  >  <=  >=
    >>> # More possible checks: where(...).matches(regex), where(...).test(your_test_func)

Tables
======

.. code-block:: python

    >>> table = db.table('name')
    >>> table.insert({'value': True})
    >>> table.all()
    [{'value': True}]

Using Middlewares
=================

.. code-block:: python

    >>> from tinydb.storages import JSONStorage
    >>> from tinydb.middlewares import CachingMiddleware
    >>> db = TinyDB('/path/to/db.json', storage=CachingMiddleware(JSONStorage))


Contributing
************

Whether reporting bugs, discussing improvements and new ideas or writing
extensions: Contributions to TinyDB-Safe are welcome! Here's how to get started:

1. Check for open issues or open a fresh issue on `GitHub Issues <https://github.com/gosmart-health/tinydb-safe/issues>`_
   to start a discussion around a feature idea or a bug.
2. Fork `the repository <https://github.com/gosmart-health/tinydb-safe>`_ on GitHub,
   create a new branch off the ``master`` branch and start making your changes
   (known as `GitHub Flow <https://docs.github.com/en/get-started/using-github/github-flow>`_).
3. Write a test which shows that the bug was fixed or that the feature works
   as expected.
4. Send a pull request and bug the maintainer until it gets merged and published ☺.

(For issues or questions related exclusively to the upstream project, please see the
`upstream TinyDB repository <https://github.com/msiemens/tinydb>`_.)

.. |Build Status| image:: https://github.com/gosmart-health/tinydb-safe/actions/workflows/ci-workflow.yml/badge.svg
   :target: https://github.com/gosmart-health/tinydb-safe/actions/workflows/ci-workflow.yml
.. |Coverage| image:: https://coveralls.io/repos/github/gosmart-health/tinydb-safe/badge.svg?branch=master
   :target: https://coveralls.io/github/gosmart-health/tinydb-safe?branch=master
.. |Version| image:: https://img.shields.io/pypi/v/tinydb-safe.svg?style=flat-square
   :target: https://pypi.org/project/tinydb-safe/
.. _Buzhug: http://buzhug.sourceforge.net/
.. _CodernityDB: https://github.com/perchouli/codernitydb
.. _MongoDB: http://mongodb.org/
