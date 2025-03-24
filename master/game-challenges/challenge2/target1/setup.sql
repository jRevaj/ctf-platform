-- Initialize the database
CREATE DATABASE IF NOT EXISTS ctf_db;
USE ctf_db;

-- Create a users table with weak credentials (intentional vulnerability)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert some users including an admin
INSERT INTO users (username, password, email, is_admin) VALUES
('admin', 'admin123', 'admin@example.com', TRUE),
('user', 'password123', 'user@example.com', FALSE),
('guest', 'guest', 'guest@example.com', FALSE);

-- Create a table for storing secrets
CREATE TABLE IF NOT EXISTS secrets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert the flag into secrets
INSERT INTO secrets (title, content) VALUES
('Database Backup Credentials', 'FLAG_PLACEHOLDER_3');

-- Create remote MySQL user with mysql_native_password authentication
-- This ensures compatibility with older MySQL clients including Node.js
CREATE USER IF NOT EXISTS 'remoteuser'@'%' IDENTIFIED WITH mysql_native_password BY 'remotep@ss';
GRANT ALL PRIVILEGES ON ctf_db.* TO 'remoteuser'@'%';

-- Create a backup user with limited privileges (for the vulnerable script)
CREATE USER IF NOT EXISTS 'backup'@'localhost' IDENTIFIED BY 'backup123';
GRANT SELECT ON ctf_db.* TO 'backup'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;