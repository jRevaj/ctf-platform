CREATE DATABASE IF NOT EXISTS ctf_db;
USE ctf_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(255)
);

INSERT INTO users (username, password) VALUES 
('admin', 'admin123'),
('user', 'user123');

GRANT SELECT ON ctf_db.* TO 'ctf-user'@'localhost';