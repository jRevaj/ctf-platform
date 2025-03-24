-- Create WordPress database
CREATE DATABASE IF NOT EXISTS wordpress;
CREATE USER 'wp_user'@'localhost' IDENTIFIED BY 'weakpassword';
GRANT ALL PRIVILEGES ON wordpress.* TO 'wp_user'@'localhost';
FLUSH PRIVILEGES;

-- Create a table with the flag
USE wordpress;
CREATE TABLE wp_secrets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    secret_name VARCHAR(255),
    flag_value VARCHAR(255)
);

-- Insert the flag
INSERT INTO wp_secrets (secret_name, flag_value) VALUES ('mysql_user_flag', 'FLAG_PLACEHOLDER_2');

-- Create root user with weak password (vulnerability)
ALTER USER 'root'@'localhost' IDENTIFIED BY 'password123';
FLUSH PRIVILEGES; 