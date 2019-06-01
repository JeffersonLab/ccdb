create schema ccdb_halld;
create schema ccdb_hallb;
create schema ccdb_test;
CREATE USER ccdb_user@'localhost';
GRANT ALL PRIVILEGES ON ccdb_halld.* TO 'ccdb_user'@'localhost';
GRANT ALL PRIVILEGES ON ccdb_hallb.* TO 'ccdb_user'@'localhost';
GRANT ALL PRIVILEGES ON ccdb_test.* TO 'ccdb_user'@'localhost';