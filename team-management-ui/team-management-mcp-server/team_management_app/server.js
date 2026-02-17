const express = require('express');
const path = require('path');
const app = express();
const PORT = 3000;

// Serve static files from the React app build directory
app.use(express.static(path.join(__dirname, 'webapp/build')));

// API routes for team management
app.use('/api', require('./routes/api'));

// The "catchall" handler: for any request that doesn't
// match one above, send back React's index.html file.
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'webapp/build/index.html'));
});

app.listen(PORT, () => {
  console.log(`Team Management UI server listening at http://localhost:${PORT}`);
});