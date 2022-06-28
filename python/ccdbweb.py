#python

if __name__ == "__main__":

    import ccdb.webgui
    # import ccdb.ccdb_pyllapi
    ccdb.webgui.cerate_ccdb_flask_app().run(debug=True)
