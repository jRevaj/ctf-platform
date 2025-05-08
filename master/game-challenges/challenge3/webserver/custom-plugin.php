<?php
/**
 * Plugin Name: Custom Plugin
 * Description: A custom plugin
 * Version: 1.0
 * Author: CTF Creator
 */

// Add a menu item in the admin dashboard
function custom_plugin_menu() {
    add_menu_page(
        'Custom Plugin', 
        'Custom Plugin', 
        'manage_options', 
        'custom-plugin', 
        'custom_plugin_page',
        'dashicons-admin-tools',
        100
    );
}
add_action('admin_menu', 'custom_plugin_menu');

// Add the flag in the response header
function custom_plugin_add_header() {
    if (is_admin() && isset($_GET['page']) && $_GET['page'] === 'custom-plugin') {
        header('X-Flag: FLAG_PLACEHOLDER_1');
    }
}
add_action('init', 'custom_plugin_add_header');

// Admin page content
function custom_plugin_page() {
    ?>
    <div class="wrap">
        <h1>Custom Plugin</h1>
        <p>This plugin is for internal use only. Nothing to see here.</p>
    </div>
    <?php
} 