// Application Configuration File
// Contains sensitive information - not secure!

module.exports = {
    // Database configurations
    database: {
        mysql: {
            host: 'target1',
            user: 'remoteuser',
            password: 'remotep@ss',
            database: 'ctf_db'
        },
        mongodb: {
            url: 'mongodb://localhost:27017',
            database: 'ctf_app',
            options: {
                useNewUrlParser: true,
                useUnifiedTopology: true
            }
        }
    },

    // Server configuration
    server: {
        port: 3000,
        hostname: '0.0.0.0'
    },

    // Logging configuration
    logging: {
        level: 'debug',
        file: '/var/log/nodeapp/app.log'
    },

    // Secret key for JWT tokens
    tokenSecret: 'super_insecure_jwt_secret_key_for_ctf_challenge',

    // API keys
    apiKeys: {
        jenkins: {
            url: 'http://target3:8080/api',
            credential: 'admin:jenkins_password'
        }
    },

    // Special flag for CTF
    flag: 'FLAG_PLACEHOLDER_5',

    // Function to verify file path - vulnerable to path traversal
    isValidFilePath: function(path) {
        // Intentionally vulnerable - doesn't properly validate path
        return path.indexOf('..') === -1;
    }
}; 