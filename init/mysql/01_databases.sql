-- create databases
CREATE DATABASE IF NOT EXISTS `npm_primary_db`;
CREATE DATABASE IF NOT EXISTS `npm_secondary_db`;
CREATE DATABASE IF NOT EXISTS `guacamole_db`;

-- create root user and grant rights
CREATE USER 'se-utilities'@'localhost' IDENTIFIED BY '53u71l17135';
GRANT ALL ON *.* TO 'se-utilities'@'localhost';