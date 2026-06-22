# Allows running the CCDB CLI as `python -m ccdb`, equivalent to the `ccdb` command.
import ccdb

if __name__ == "__main__":
    ccdb.init_ccdb_console()
