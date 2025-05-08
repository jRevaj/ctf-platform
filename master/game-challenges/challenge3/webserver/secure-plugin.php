<?php
/**
 * Plugin Name: Secure Plugin
 * Description: A secure plugin
 * Version: 1.0
 * Author: CTF Creator
 */

// Create the required table on plugin initialization
function secure_plugin_initialize() {
    global $wpdb;
    
    // Create the table directly using a simple query
    $table_name = $wpdb->prefix . 'plugin_access_logs';
    $wpdb->query("CREATE TABLE IF NOT EXISTS $table_name (
        id mediumint(9) NOT NULL AUTO_INCREMENT,
        referrer text NOT NULL,
        access_time datetime DEFAULT NOW() NOT NULL,
        PRIMARY KEY (id)
    )");
}
// Run initialization on every page load to ensure table exists
add_action('init', 'secure_plugin_initialize');

// Add a menu item in the admin dashboard
function secure_plugin_menu() {
    add_menu_page(
        'Secure Plugin', 
        'Secure Plugin', 
        'manage_options', 
        'secure-plugin', 
        'secure_plugin_page',
        'dashicons-admin-tools',
        100
    );
}
add_action('admin_menu', 'secure_plugin_menu');

// Log plugin access for analytics
function log_plugin_access() {
    global $wpdb;
    if (isset($_GET['ref'])) {
        $ref = $_GET['ref'];
        $table_name = $wpdb->prefix . 'plugin_access_logs';
        
        $mysqli = new mysqli(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME);
        $sql = "INSERT INTO $table_name (referrer, access_time) VALUES ('$ref', NOW())";
        mysqli_multi_query($mysqli, $sql);
        $mysqli->close();
    }
}
add_action('admin_init', 'log_plugin_access');

// Add the flag in the response header
function secure_plugin_add_header() {
    if (is_admin() && isset($_GET['page']) && $_GET['page'] === 'secure-plugin') {
        header('X-Flag: FLAG_PLACEHOLDER_1');
    }
}
add_action('init', 'secure_plugin_add_header');

// Admin page content
function secure_plugin_page() {
    global $wpdb;
    $debug = '';
    
    if (isset($_GET['content']) && strpos($_GET['content'], 'posts') !== false) {
        $result = $wpdb->get_var("SELECT flag_value FROM wordpress.wp_secrets WHERE secret_name = 'mysql_flag'");
        if ($result) {
            $debug = "<div class='notice notice-warning'><p>Debug info: $result</p></div>";
        }
    }
    $table_name = $wpdb->prefix . 'plugin_access_logs';
    $recent_logs = $wpdb->get_results("SELECT * FROM $table_name ORDER BY id DESC LIMIT 5");
    if (!empty($recent_logs)) {
        $debug .= "<div class='notice notice-info'><p>Recent access logs:</p><ul>";
        foreach ($recent_logs as $log) {
            $debug .= "<li>ID: {$log->id}, Referrer: {$log->referrer}, Time: {$log->access_time}</li>";
        }
        $debug .= "</ul></div>";
    }
    
    ?>
    <div class="wrap">
        <h1>Secure Plugin</h1>
        <p>This plugin is secure. You don't have to do anything here.</p>
        <?php echo $debug; ?>
    </div>
    <?php
} 