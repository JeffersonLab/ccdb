CREATE DATABASE IF NOT EXISTS test_ccdb;

-- Create the user for external access
CREATE USER 'test_user'@'%' IDENTIFIED BY 'test_password';

-- Grant all privileges on the test database to the user
GRANT ALL PRIVILEGES ON test_ccdb.* TO 'test_user'@'%';

-- Apply the privilege changes
FLUSH PRIVILEGES;

-- Switch to the test database
USE test_ccdb;