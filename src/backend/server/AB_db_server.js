/* Server-side script written in Node.js using the Express.js framework. 
Sets up a simple web server that connects to a MySQL database and serves 
up a single route for fetching data.*/
require('dotenv').config();
const express = require('express');
const mysql = require('mysql2');

const app = express();
const port = 3000;

const db = mysql.createConnection({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME
});

db.connect((err) => {
  if (err) {
    console.error('Error connecting to the database', err);
    process.exit(1);
  }
  console.log('Connected to the database');
});

app.post('/store-data', express.json(), (req, res) => {
  const data = req.body;
  let sql = 'INSERT INTO mytable SET ?';
  db.query(sql, data, (err, result) => {
    if (err) {
      console.error('Error storing data', err);
      return res.status(500).send('An error occurred while storing data');
    }
    res.send('Data stored successfully');
  });
});

app.get('/fetch-data', (req, res) => {
  let sql = 'SELECT * FROM mytable';
  db.query(sql, (err, result) => {
    if (err) {
      console.error('Error fetching data', err);
      return res.status(500).send('An error occurred while fetching data');
    }
    res.send(result);
  });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});

