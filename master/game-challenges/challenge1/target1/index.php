<?php
$host = 'localhost';
$dbname = 'ctf_db';
$username = 'ctf-user';
$password = 'admin123';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    $stmt = $pdo->query("SELECT * FROM secrets");
    $secrets = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "<h1>Secrets</h1>";
    
    foreach($secrets as $secret) {
        echo "Secret: " . htmlspecialchars($secret['secret_data']) . "<br>";
    }
    
} catch(PDOException $e) {
    echo "Connection failed: " . $e->getMessage();
}
?>