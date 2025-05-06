<?php
/**
 * Plugin Name: Vulnerable Plugin
 * Plugin URI: http://example.com/vulnerable-plugin
 * Description: A deliberately vulnerable plugin for CTF challenge
 * Version: 1.0
 * Author: CTF Creator
 */

// Add hook for admin page
add_action('admin_menu', 'vulnerable_plugin_menu');

// Register menu page
function vulnerable_plugin_menu() {
    add_menu_page(
        'Vulnerable Plugin', 
        'Vulnerable Plugin', 
        'manage_options',
        'vulnerable-plugin', 
        'vulnerable_plugin_page',
        'dashicons-admin-generic'
    );
}

// Vulnerable plugin page with RCE
function vulnerable_plugin_page() {
    // Add flag to response header
    header('X-Flag: FLAG_PLACEHOLDER_1');
    
    echo '<div class="wrap">';
    echo '<h1>Vulnerable Plugin Settings</h1>';
    
    // Vulnerable file upload
    if (isset($_FILES['upload'])) {
        $upload_dir = wp_upload_dir();
        $target_file = $upload_dir['path'] . '/' . basename($_FILES['upload']['name']);
        
        // Vulnerable to path traversal
        if (move_uploaded_file($_FILES['upload']['tmp_name'], $target_file)) {
            echo '<div class="updated notice"><p>File uploaded successfully!</p></div>';
        }
    }
    
    // Vulnerable code - allows direct command execution with basic filtering
    if (isset($_GET['cmd'])) {
        $cmd = $_GET['cmd'];
        // Basic filter that can be bypassed
        if (strpos($cmd, 'cat') === false && strpos($cmd, 'ls') === false) {
            echo '<div class="updated notice"><p>Command Output:</p>';
            echo '<pre>';
            system($cmd); // Vulnerable to RCE
            echo '</pre></div>';
        } else {
            echo '<div class="error notice"><p>Command not allowed!</p></div>';
        }
    }
    
    echo '<form method="post" enctype="multipart/form-data">';
    echo '<input type="hidden" name="page" value="vulnerable-plugin">';
    echo '<p>Upload a file: <input type="file" name="upload"></p>';
    echo '<p><input type="submit" class="button button-primary" value="Upload File"></p>';
    echo '</form>';
    
    echo '<form method="get">';
    echo '<input type="hidden" name="page" value="vulnerable-plugin">';
    echo '<p>Enter system command to check server status: <input type="text" name="cmd" value=""></p>';
    echo '<p><input type="submit" class="button button-primary" value="Run Command"></p>';
    echo '</form>';
    echo '</div>';
}
?> 