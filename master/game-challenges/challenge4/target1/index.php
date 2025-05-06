<?php
$host = 'localhost';
$dbname = 'ctf_db';
$username = 'ctf-user';
$password = 'starthere';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    $stmt = $pdo->query("SELECT * FROM secrets");
    $secrets = $stmt->fetchAll();
    
    echo "<h1>Secrets</h1>";
    foreach($secrets as $secret) {
        echo "Secret: " . htmlspecialchars($secret['secret']) . "<br>";
    }
    
} catch(PDOException $e) {
    echo "Connection failed: " . $e->getMessage();
}
?>