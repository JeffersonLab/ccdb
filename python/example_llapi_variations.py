"""

Example of using Low Level python API to readout data from CCDB

"""

import os

if __name__ == "__main__":

    ccdb_home = os.environ["CCDB_HOME"]  # This environment variable should be set!

    # Set env. variable PYTHONPATH=$CCDB_HOME/python;$PYTHONPATH
    # or sys.path.append(os.path.join(ccdb_home, "python"))
    import ccdb
    from ccdb import Directory, TypeTable, Assignment, ConstantSet, Variation
    from sqlalchemy import desc

    sqlite_connect_str = "sqlite:///" + os.path.join(ccdb_home, "sql", "ccdb.sqlite")

    # create CCDB api class
    provider = ccdb.AlchemyProvider()  # this class has all CCDB manipulation functions
    provider.connect(sqlite_connect_str)  # use usual connection string to connect to database
    provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    # create parent variation
    var_parent = provider.create_variation("test_pyllapi_parent")  # Parent is omitted => parent is 'default'

    # create child variation. We specify its name, comment and parent variation
    var = provider.create_variation("test_pyllapi", "Test how to work from py llapi", "test_pyllapi_parent")
    print("Created variations: ")
    print("{} , parent {}".format(var, var.parent))                 # 'test_pyllapi' has parent 'test_pyllapi_parent'
    print("{} , parent {}".format(var_parent, var_parent.parent))   # 'test_pyllapi_parent' has 'parent default'

    # Modify variation comment
    var_parent.comment = "We changed comment"
    provider.update_variation(var_parent)
    var_parent = provider.get_variation("test_pyllapi_parent")     # reread variation from DB to check comment
    print("test_var_parent comment changed to: '{}'".format(var_parent.comment))
    print

    # Modify variation parent
    var_new_parent = provider.create_variation("test_pyllapi_new_parent", "Test new parent")
    var.parent = var_new_parent
    provider.update_variation(var)

    # Just to be sure the magic works, we reread variation (one doesn't have to reread variations after update actually)
    print("Changed variation parent: ")
    print("{} , parent {}".format(var, var.parent))                    # 'test_pyllapi' has parent 'test_pyllapi_parent'
    print("{} , parent {}".format(var_new_parent, var_parent.parent))  # 'test_pyllapi_parent' has 'parent default'

    # Delete variations
    provider.delete_variation(var_parent)
    provider.delete_variation(var_new_parent)
    provider.delete_variation(var)

    # Lets get last 3 variations and see, that we really deleted those we used before
    # We will use SQL Alchemy for that
    variations = provider.session.query(Variation).order_by(desc(Variation.id)).limit(3).all()

    print("Last 3 variations (after we deleted experimental ones)")
    for variation in variations:
        print(variation)

    # How SQLAlchemy query works:
    # provider.session - gives access to sql alchemy
    # .query(Variation) - The result will be a collection of variations
    # .order_by(desc(Variation.id)) - The results are ordered by variation db ids. The order is descending
    # .limit(3) - Take no more than 3 results
    # .all() - return all what we've got. One could use .one(), .first(), count() instead of .all() to get results




