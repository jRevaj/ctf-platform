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
    
    // Vulnerable code - allows direct command execution
    if (isset($_GET['cmd'])) {
        echo '<div class="updated notice"><p>Command Output:</p>';
        echo '<pre>';
        system($_GET['cmd']); // Vulnerable to RCE
        echo '</pre></div>';
    }
    
    echo '<form method="get">';
    echo '<input type="hidden" name="page" value="vulnerable-plugin">';
    echo '<p>Enter system command to check server status: <input type="text" name="cmd" value=""></p>';
    echo '<p><input type="submit" class="button button-primary" value="Run Command"></p>';
    echo '</form>';
    echo '</div>';
}
?> 