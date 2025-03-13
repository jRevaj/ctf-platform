<?php
/**
 * Hidden admin panel for CTF challenge
 */

// Basic authentication
$valid_username = 'admin';
$valid_password = 'super_secret_admin_password';

$authenticated = false;

// Check for authentication attempt
if (isset($_POST['username']) && isset($_POST['password'])) {
    if ($_POST['username'] === $valid_username && $_POST['password'] === $valid_password) {
        $authenticated = true;
    }
}

// Output appropriate content
header('Content-Type: text/html');
?>
<!DOCTYPE html>
<html>
<head>
    <title>WordPress Secret Admin Panel</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: 0 auto; }
        .login-form { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .secret-panel { background: #e0f7fa; padding: 20px; border-radius: 5px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 10px 0; }
        input[type="submit"] { background: #0073aa; color: white; border: none; padding: 10px 20px; cursor: pointer; }
        .flag { background: #000; color: #fff; padding: 10px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>WordPress Secret Admin Panel</h1>
        
        <?php if (!$authenticated): ?>
            <div class="login-form">
                <h2>Login Required</h2>
                <form method="post">
                    <div>
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div>
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <div>
                        <input type="submit" value="Login">
                    </div>
                </form>
            </div>
        <?php else: ?>
            <div class="secret-panel">
                <h2>Welcome, Administrator</h2>
                <p>This panel contains sensitive information not accessible through the regular admin interface.</p>
                
                <h3>System Information</h3>
                <ul>
                    <li>WordPress Version: 6.0.0</li>
                    <li>PHP Version: <?php echo phpversion(); ?></li>
                    <li>Server: <?php echo $_SERVER['SERVER_SOFTWARE']; ?></li>
                </ul>
                
                <h3>Security Flag</h3>
                <div class="flag">FLAG_PLACEHOLDER_3</div>
                
                <h3>Sensitive Configuration</h3>
                <p>Database credentials and other sensitive information would be listed here...</p>
            </div>
        <?php endif; ?>
    </div>
</body>
</html> 