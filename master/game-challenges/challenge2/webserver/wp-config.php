<?php
/**
 * The base configuration for WordPress
 */

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'wordpress' );

/** Database username */
define( 'DB_USER', 'wp_user' );

/** Database password */
define( 'DB_PASSWORD', 'password' );

/** Database hostname */
define( 'DB_HOST', 'localhost' );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**#@+
 * Authentication unique keys and salts.
 */
define('AUTH_KEY',         'c7HZa+|gK-X)2_4i+~}3|Yt]Z}[N<-?vK|w-(c+p|4iI(r-IEPUvo-+Ry%|+MYw>');
define('SECURE_AUTH_KEY',  '1y-O-%LG2xnP6|}OI]^_rW+)W?=V%^ZO+3z]I-| D*&w-JD*?K9p-J-r+F<|vNSW');
define('LOGGED_IN_KEY',    'Q#@3e21k4KWy3u+D+Qw-y.!VeRRQ+&{#i!X`*YQnJu-gn!l$lj2c;yE:Rya-9bL$');
define('NONCE_KEY',        'yHQm+{@|5NNc:LD74a7|,E?Vr_H~c$>h&1&*v6Xw&;2LBw`tE@#UJ:O@;~@8-s|z');
define('AUTH_SALT',        '2UO$BT(f$+-}+UGpZ2oc@WR+Yl3R[/AEFOQc]y+XL`v+OFnl@~lmI0tL#H)lv@DH');
define('SECURE_AUTH_SALT', 'aDTHEm<3ydP0EQ|wm+`F#/Cj(T{n~<fNu6RV|Z>vj+D&j{XCZ5mM~U|],^xc{G:j');
define('LOGGED_IN_SALT',   'I(tAF]Mh-V}Iw.CK1[uuM+2%EJ1JgcQ@~qvRgxRz-EWW(lMKEi!ib-7g)1`Md-8p');
define('NONCE_SALT',       'dTEOw/`b,:yw]K/t}_>-lN`kpHq(5&e,vJRDu$}CW5IyTRY)P;WY^Pey<e:YOxAI');

/**#@-*/

/**
 * WordPress database table prefix.
 */
$table_prefix = 'wp_';

/**
 * For developers: WordPress debugging mode.
 */
define( 'WP_DEBUG', false );

// For wp-cli compatibility
define('WP_SITEURL', 'http://localhost');
define('WP_HOME', 'http://localhost');

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php'; 