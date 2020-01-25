
## Compilation

```bash

cd <compilation dir>
cmake -DCMAKE_INSTALL_PREFIX=<install dir> $CCDB_HOME/cpp
cmake --build <compilation dir> --target all -- -j 16
```

### Ubuntu:
libsqlite3-dev

