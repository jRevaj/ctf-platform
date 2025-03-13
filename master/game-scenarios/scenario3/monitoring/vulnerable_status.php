<?php
// Vulnerable status page with XSS vulnerability
// This is a simplified version for the CTF challenge

// Set content type
header("Content-Type: text/html");

// Get the hostname parameter (vulnerable to XSS)
$hostname = isset($_GET['hostname']) ? $_GET['hostname'] : 'localhost';

// Hidden flag in HTML comment
$flag = "FLAG_PLACEHOLDER_12";
?>
<!DOCTYPE html>
<html>
<head>
    <title>Nagios Status Page</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #0066cc; }
        .status-ok { background-color: #dff0d8; padding: 10px; border: 1px solid #d6e9c6; }
        .status-warning { background-color: #fcf8e3; padding: 10px; border: 1px solid #faebcc; }
        .status-critical { background-color: #f2dede; padding: 10px; border: 1px solid #ebccd1; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Nagios Status Page</h1>
    
    <!-- XSS vulnerability: hostname parameter is not sanitized -->
    <h2>Status for host: <?php echo $hostname; ?></h2>
    
    <form method="get">
        <label for="hostname">Enter hostname:</label>
        <input type="text" id="hostname" name="hostname" value="<?php echo htmlspecialchars($hostname); ?>">
        <input type="submit" value="Check Status">
    </form>
    
    <div class="status-ok">
        <h3>Current System Status</h3>
        <p>All systems are operational.</p>
    </div>
    
    <h3>Service Status</h3>
    <table>
        <tr>
            <th>Service</th>
            <th>Status</th>
            <th>Last Check</th>
        </tr>
        <tr>
            <td>HTTP</td>
            <td>OK</td>
            <td><?php echo date('Y-m-d H:i:s'); ?></td>
        </tr>
        <tr>
            <td>SSH</td>
            <td>OK</td>
            <td><?php echo date('Y-m-d H:i:s', time() - 300); ?></td>
        </tr>
        <tr>
            <td>Database</td>
            <td>OK</td>
            <td><?php echo date('Y-m-d H:i:s', time() - 600); ?></td>
        </tr>
    </table>
    
    <!-- Hidden flag in HTML comment -->
    <!-- 
        Admin note: Need to fix XSS vulnerability in hostname parameter
        Flag: <?php echo $flag; ?>
    -->
</body>
</html> 