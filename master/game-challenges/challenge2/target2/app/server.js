const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const { MongoClient } = require('mongodb');
const mysql = require('mysql');
const config = require('./config');

// Create Express app
const app = express();
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Logging middleware - vulnerable to log poisoning
app.use((req, res, next) => {
    const logEntry = `${new Date().toISOString()} - ${req.ip} - ${req.method} ${req.url} - User-Agent: ${req.headers['user-agent']}\n`;
    fs.appendFile(config.logging.file, logEntry, (err) => {
        if (err) console.error('Error writing to log file:', err);
    });
    next();
});

// MongoDB connection
let db;
MongoClient.connect(config.database.mongodb.url, config.database.mongodb.options)
    .then(client => {
        console.log('Connected to MongoDB');
        db = client.db(config.database.mongodb.database);
    })
    .catch(err => {
        console.error('MongoDB connection error:', err);
    });

// MySQL connection
const mysqlConnection = mysql.createConnection({
    host: config.database.mysql.host,
    user: config.database.mysql.user,
    password: config.database.mysql.password,
    database: config.database.mysql.database
});

mysqlConnection.connect(err => {
    if (err) {
        console.error('MySQL connection error:', err);
    } else {
        console.log('Connected to MySQL database');
    }
});

// Routes
app.get('/', (req, res) => {
    res.send('Vulnerable Node.js Application');
});

// Vulnerable endpoint - Path Traversal
app.get('/read-file', (req, res) => {
    const fileName = req.query.file;
    
    // Vulnerable path validation - can be bypassed with %2e%2e/
    if (fileName && config.isValidFilePath(fileName)) {
        const filePath = path.join('/target2/app/public', fileName);
        
        fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) {
                return res.status(404).send({ error: 'File not found' });
            }
            res.send({ content: data });
        });
    } else {
        res.status(400).send({ error: 'Invalid file path' });
    }
});

// Endpoint to query MySQL
app.get('/mysql-data', (req, res) => {
    const query = "SELECT * FROM users";
    
    mysqlConnection.query(query, (err, results) => {
        if (err) {
            return res.status(500).send({ error: 'Database error' });
        }
        res.send({ data: results });
    });
});

// Secret endpoint with credentials in code - another vulnerability
app.get('/jenkins-integration', (req, res) => {
    // Hardcoded credentials for Jenkins
    const jenkinsUrl = 'http://target3:8080';
    const jenkinsUser = 'admin';
    const jenkinsPass = 'jenkins_password';
    
    res.send({
        status: 'Connected to Jenkins',
        message: 'Jenkins integration is configured'
    });
});

// Add a test endpoint to verify MySQL connectivity
app.get('/testdb', (req, res) => {
    if (!mysqlConnection || mysqlConnection.state === 'disconnected') {
        return res.status(500).json({ error: 'MySQL connection failed' });
    }
    
    mysqlConnection.query('SELECT 1 as test', (err, results) => {
        if (err) {
            console.error('MySQL query error:', err);
            return res.status(500).json({ error: 'MySQL query failed', details: err.message });
        }
        
        res.status(200).json({ message: 'MySQL connection successful', data: results });
    });
});

// Start the server
app.listen(config.server.port, config.server.hostname, () => {
    console.log(`Server running at http://${config.server.hostname}:${config.server.port}/`);
});

// Create public directory if it doesn't exist
if (!fs.existsSync('/target2/app/public')) {
    fs.mkdirSync('/target2/app/public', { recursive: true });
    fs.writeFileSync('/target2/app/public/test.txt', 'This is a test file.');
} 