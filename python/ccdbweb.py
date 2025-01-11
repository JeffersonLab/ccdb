import ccdb.webgui

# Create the Flask app
app = ccdb.webgui.cerate_ccdb_flask_app()

if __name__ == "__main__":
    # Run the app in debug mode when executed directly
    app.run(debug=True)
