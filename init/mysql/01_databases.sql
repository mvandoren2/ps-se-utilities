-- create databases
CREATE DATABASE IF NOT EXISTS `npm_primary_db`;
CREATE DATABASE IF NOT EXISTS `npm_secondary_db`;
CREATE DATABASE IF NOT EXISTS `guacamole_db`;

-- create root user and grant rights
CREATE USER 'se-utilities'@'proxy' IDENTIFIED BY '53u71l17135';
CREATE USER 'se-utilities'@'rw-proxy' IDENTIFIED BY '53u71l17135';
CREATE USER 'se-utilities'@'guacamole' IDENTIFIED BY '53u71l17135';
GRANT ALL ON npm_primary_db.* TO 'se-utilities'@'proxy';
GRANT ALL ON npm_secondary_db.* TO 'se-utilities'@'rw-proxy';
GRANT ALL ON guacamole_db.* TO 'se-utilities'@'guacamole';