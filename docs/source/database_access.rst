Database Access
===============

The output of the exposures are stored in a csv file in the
path set by the user on the yaml configuration file. The default
path is ``pandora/database.csv``. 

The database can be accessed
using the ``get_db()`` method:

.. code-block:: python

   db = pandora.get_db()
   print(db)

It is a pandas dataframe with columns defined in ``pandora.database.columns_map``:

The columns are standard and are hard coded in the
``pandora.database.columns_map`` module. 

.. code-block:: python

   import pandora.database.columns_map as columns_map
   print(columns_map.COLUMN_DEFINITIONS.keys())

   # the default values are
   print(columns_map.DEFAULT_VALUES)
