"""

Example of using Low Level python API to manage or change variations

"""

import os

if __name__ == "__main__":

    ccdb_home = os.environ["CCDB_HOME"]  # This environment variable should be set!

    # Set env. variable PYTHONPATH=$CCDB_HOME/python;$PYTHONPATH
    # or sys.path.append(os.path.join(ccdb_home, "python"))
    import ccdb
    from ccdb import Variation
    from sqlalchemy import desc

    sqlite_connect_str = "sqlite:///" + os.path.join(ccdb_home, "sql", "ccdb.sqlite")

    # create CCDB api class
    provider = ccdb.AlchemyProvider()  # this class has all CCDB manipulation functions
    provider.connect(sqlite_connect_str)  # use usual connection string to connect to database
    provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    # create parent variation
    parent_var = provider.create_variation("test_pyllapi_parent")  # Parent is omitted => parent is 'default'

    # create child variation. We specify its name, comment and parent variation
    child_var = provider.create_variation("test_pyllapi", "Test how to work from py llapi", "test_pyllapi_parent")
    print("Created variations: ")
    print("{} , parent {}".format(child_var, child_var.parent))     # 'test_pyllapi' has parent 'test_pyllapi_parent'
    print("{} , parent {}".format(parent_var, parent_var.parent))   # 'test_pyllapi_parent' has 'parent default'

    # Modify variation comment
    parent_var.comment = "We changed comment"
    provider.update_variation(parent_var)
    parent_var = provider.get_variation("test_pyllapi_parent")     # reread variation from DB to check comment
    print("test_var_parent comment changed to: '{}'".format(parent_var.comment))
    print

    # Modify variation parent
    new_parent_var = provider.create_variation("test_pyllapi_new_parent", "Test new parent")
    child_var.parent = new_parent_var
    provider.update_variation(child_var)

    # Just to be sure the magic works, we reread variation (one doesn't have to reread variations after update actually)
    print("Changed variation parent: ")
    print("{} , parent {}".format(child_var, child_var.parent))        # 'test_pyllapi' has parent 'test_pyllapi_parent'
    print("{} , parent {}".format(new_parent_var, parent_var.parent))  # 'test_pyllapi_parent' has 'parent default'
    print

    # Delete variations
    provider.delete_variation(parent_var)
    provider.delete_variation(new_parent_var)
    provider.delete_variation(child_var)

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
