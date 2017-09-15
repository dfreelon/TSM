===
TSM
===

Twitter Subgraph Manipulator by `Deen Freelon`_

.. _Deen Freelon: dfreelon@gmail.com

In short, TSM is a Python module that contains a few functions for analyzing Twitter and Twitter-like (i.e., directed and very sparse with community structure) network data. I wrote it for my own research purposes but thought someone out there might find it useful.

-------------------------
Installation instructions
-------------------------

**Now available in PyPI!** Just use: ``pip3 install tsm``. But when installing from PyPI you need to use ``from tsm import tsm`` as ``import tsm`` won't work by itself.

Alternatively, you can simply install tsm's dependencies manually and move ``tsm.py`` into your PYTHONPATH directory.

--------
Features
--------

Here are some of the things TSM can do:

- Support very large communities (millions of nodes/edges)--the only limit is your computer's memory
- Extract retweets and @-mentions into edgelist format for network
  analysis and visualization
- Partition networks into communities, isolate the N largest
  communities, and identify the most-connected users in each community
- Measure the insularity of network communities (using EI indices) to
  determine the extent to which each looks like an echo chamber
- Measure the overlap between network communities to determine which
  ones interact more and less often
- Get the top retweets in a Twitter dataset and rank them by N of
  retweets and by community
- Track Twitter (or other) communities over time: compute similarity
  scores (weighted or unweighted Jaccard coefficients) for partitioned
  network communities drawn from the same dataset at two different
  time slices
- Discover which nodes intermediate between which communities
- Find the most-used hashtags in each community (or dataset)
- Find the most-used hyperlinks or web domains in each community (or dataset)

See ``tsm.py`` for a full description of TSM's functions and how to use them. The module should work as long as NetworkX and ``python-louvain`` are installed.

------------
Requirements
------------

Here's what you need to use TSM:

- ``tsm.py``, the TSM Python module provided here
- ``python-louvain``, Thomas Aynaud's Python implementation of the Louvain method of network community detection. (https://bitbucket.org/taynaud/python-louvain)
- ``NetworkX``, a Python module for general network analysis. (http://networkx.github.io/)
- ``Python 3.x``, needed for Unicode support. (https://www.python.org/)

-------------
Documentation
-------------

The ``TSM demo files.zip`` file contains two IPython notebooks and a Twitter ID file that can be used to demo many of TSM's functions. Code and instructions are provided to hydrate the Twitter ID file. For testing purposes, here is a very brief (fabricated) sample demonstrating how input data for the ``t2e`` function should be formatted in a plain text file. This sample was created by Devin Gaffney (`@DGaffney <https://github.com/DGaffney>`_)::

    dgaff,"Twitter is pretty fun, isn't it, @dfreelon?"
    dfreelon,Yes indeed @dgaff - @some_other_user weigh in?
    some_other_user,Of course twitter is grand. Mostly because of @dril.
    dril,Some weird tweet no one understands but everyone favorites @some_other_user
    cnnbrk,Looks like @dril just tweeted
    
---------------
Acknowledgments
---------------

I gratefully acknowledge funding support from the US Institute of Peace in creating this module.
