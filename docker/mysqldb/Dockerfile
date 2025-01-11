# Use the official MySQL image as the base
FROM mysql:latest

# Set the MySQL root password
# ENV MYSQL_ROOT_PASSWORD=root_password
# Set the MySQL database name so the ccdb.mysql.sql can proceed
# ENV MYSQL_DATABASE=test_ccdb

# Copy SQL initialization scripts into the MySQL entrypoint initialization directory
COPY sql/test_user_init.sql /docker-entrypoint-initdb.d/001-test_user_init.sql
COPY sql/ccdb.mysql.sql /docker-entrypoint-initdb.d/002-ccdb.mysql.sql

EXPOSE 3306
