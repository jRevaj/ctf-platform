<?php
/**
 * Hidden admin page with a flag
 */

// Load WordPress core
define('WP_USE_THEMES', false);
require_once(dirname(__FILE__) . '/../wp-load.php');

// Check if user is logged in as an admin
if (!current_user_can('administrator')) {
    status_header(404);
    wp_die('Page not found');
    exit;
}

// Display the flag
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secret Admin Page</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            margin: 20px;
        }
        .container {
            background-color: white;
            border: 1px solid #ddd;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            color: #23282d;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .flag {
            background-color: #f0f0f1;
            padding: 15px;
            border-left: 4px solid #00a0d2;
            margin: 20px 0;
            font-family: monospace;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Secret Admin Page</h1>
        <p>Congratulations on finding the hidden admin page!</p>
        <div class="flag">
            <strong>Flag:</strong> FLAG_PLACEHOLDER_3
        </div>
        <p>This page is not linked from anywhere in the admin dashboard and should remain confidential.</p>
    </div>
</body>
</html> 