// Main application file
const express = require('express');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

// API routes
app.get('/', (req, res) => {
  res.send('Corporate Application API');
});

app.get('/api/status', (req, res) => {
  res.json({ status: 'ok', version: '1.0.0' });
});

// Protected route
app.get('/api/admin', (req, res) => {
  const apiKey = req.headers['x-api-key'];
  
  if (apiKey !== process.env.API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  res.json({
    message: 'Admin panel',
    secret: 'This is a secret admin endpoint',
    environment: process.env.NODE_ENV || 'development'
  });
});

// Start server
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
}); 