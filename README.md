bricks - configure semplice features
====================================


What it is?
-----------

bricks is a GTK+3 GUI tool, written in Python, that permits to manage
the "feature meta-packages" provided by Semplice since Semplice 4.


How does it work?
-----------------

A feature meta-package depends on the packages that provide the function.
To "enable" a feature, that package is installed.
Instead, to "disable" one, the feature meta-package and its dependencies
are removed.

engine
------

bricks.engine is the library that interfaces with python-apt.

How to add a feature?
---------------------

Just edit features.py (features dictionary).
Then add the feature on the features_order tuple.
