<?php
$host = 'localhost';
$dbname = 'ctf_db';
$username = 'ctf-user';
$password = '';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    $stmt = $pdo->query("SELECT * FROM users");
    $users = $stmt->fetchAll();
    
    echo "<h1>Users</h1>";
    foreach($users as $user) {
        echo "Username: " . htmlspecialchars($user['username']) . "<br>";
    }
    
} catch(PDOException $e) {
    echo "Connection failed: " . $e->getMessage();
}
?>