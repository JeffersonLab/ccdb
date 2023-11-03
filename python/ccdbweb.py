#python

if __name__ == "__main__":

    import ccdb.webgui
    # import ccdb.ccdb_pyllapi
    app = ccdb.webgui.cerate_ccdb_flask_app()
    app.run(debug=True)
