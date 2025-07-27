/* Server-side script written in Node.js using the Express.js framework.
Implements a basic user authentication system using the passport-local
strategy for Passport.js.*/

require('dotenv').config({ path: 'AB_user_auth_ss.env' });
console.log('dotenv loaded');

const sessionSecret = process.env.SESSION_SECRET;

// Check if SESSION_SECRET is defined
if (!sessionSecret) {
  console.error("SESSION_SECRET is not defined in environment variables or .env file");
  process.exit(1); // Exit the application
}

console.log('SESSION_SECRET:', sessionSecret);

const { createPool } = require('mysql2');
const express = require('express');
const app = express();
const LocalStrategy = require('passport-local').Strategy;
const bcrypt = require('bcrypt');
const { check, validationResult } = require('express-validator');
const passport = require('passport');
const flash = require('express-flash');
const session = require('express-session');
const methodOverride = require('method-override');
const path = require('path');

// Create a connection to your database
const db = createPool({
  host: 'ls-5a1a450da9b72ee816d64ca751459a1171836a83.c9iwyumu4w7q.us-west-2.rds.amazonaws.com',
  user: 'dbmasteruser',
  password: 'Wasfiothman1',
  database: 'newab',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// Check database connection
console.log('Connecting to the database');

// Define initializePassport function
const initializePassport = require('./passport-config.js');

initializePassport(
  passport,
  async email => {
    try {
      const [rows, fields] = await db.execute("SELECT * FROM ab_users WHERE Email = ?", [email]);
      return rows[0]; // Assuming email is unique, so return the first row
    } catch (error) {
      console.error('Error finding user:', error);
      return null;
    }
  },
  async id => {
    try {
      const [rows, fields] = await db.execute("SELECT * FROM ab_users WHERE UserID = ?", [id]);
      return rows[0]; // Assuming UserID is unique, so return the first row
    } catch (error) {
      console.error('Error finding user:', error);
      return null;
    }
  }
);

// Define middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.static(path.join(__dirname, 'views')));
app.use(express.urlencoded({ extended: false }));
app.use(flash());
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false
}));
app.use(passport.initialize());
app.use(passport.session());
app.use(methodOverride('_method'));

app.get('/', checkAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, 'AB_SignIn.html'));
});

// Route to get all users
app.get('/user', async (req, res) => {
  try {
    const [rows, fields] = await db.execute("SELECT * FROM ab_users");
    console.log('Query results:', rows);
    res.json(rows);
  } catch (error) {
    console.error('Error executing query:', error);
    res.status(500).send('Internal Server Error');
  }
});

const { v4: uuidv4 } = require('uuid');

// Route to create a new user
app.post('/SignUp', checkNotAuthenticated, async (req, res) => {
  try {
      // Generate a hashed password
      const hashedPassword = await bcrypt.hash(req.body.Password, 12);

      // Prepare user data
      const userData = {
        FirstName: req.body.FirstName,
        LastName: req.body.LastName,
        Email: req.body.Email,
        Password: hashedPassword,
        Birthday: req.body.Birthday,
        PhoneNumber: req.body.PhoneNumber
      };

      // Insert the user
      const insertResult = await db.execute("INSERT INTO ab_users SET ?", userData);

      // Check if the insertion was successful
      if (insertResult[0].affectedRows === 1) {
        // Display a confirmation message
        console.log('User created successfully:', req.body.Email);
        
        // Redirect the user to the confirmation page
        return res.redirect('/AB_SignUp_pg3.html');
      } else {
        // Display an error message if the insertion failed
        console.error('User creation failed');
  
        // Send an error response to the client
        return res.status(500).json({ message: 'Failed to create user. Please try again.' });
        }

  } catch (error) {
      // Display error message if the user creation fails
      console.error('Error during sign-up process:', error);
      res.redirect('/SignUp'); // Redirect back to the signup page
  }
});

// Sign-in route
app.get('/SignIn', checkNotAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, 'AB_SignIn.html'));
});

// Define an array of validation checks
const signUpValidation = [
  check('Email')
    .isEmail()
    .withMessage('Please enter a valid email address.'),
  check('Password')
    .isLength({ min: 12 })
    .withMessage('Password must be at least 8 characters long.')
    // Add more validation checks as needed
];

// Sign-up post request
app.post('/SignUp', signUpValidation, checkNotAuthenticated, async (req, res) => {
  try {
    // Perform validation checks
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      // If there are validation errors, send them to the client
      return res.status(400).json({ errors: errors.array() });
    }
    
    // Generate a hashed password
    const hashedPassword = await bcrypt.hash(req.body.Password, 12);

    // Prepare user data
    const userData = {
      FirstName: req.body.FirstName,
      LastName: req.body.LastName,
      Email: req.body.Email,
      Password: hashedPassword,
      Birthday: req.body.Birthday,
      PhoneNumber: req.body.PhoneNumber
    };

    // Insert the user
    const insertResult = await db.execute("INSERT INTO ab_users SET ?", userData);

    // Display a confirmation message
    console.log('User created successfully:', req.body.Email);

    // Redirect the user to the confirmation page
    return res.redirect('/AB_SignUp_pg3.html');
  } catch (error) {
    // Display error message if the user creation fails
    console.error('Error during sign-up process:', error);
    
    // Send a more descriptive error message to the client
    return res.status(500).json({ message: 'An error occurred during the sign-up process. Please try again.' });
  }
});

// Sign-in post request
app.post('/SignIn', checkNotAuthenticated, passport.authenticate('local', {
  successRedirect: '/',
  failureRedirect: '/SignIn',
  failureFlash: true,
}));

// Implement Signout route using logout
app.get('/logout', (req, res) => {
  req.logout();
  res.redirect('/SignIn');
});
  
  function checkAuthenticated(req, res, next) {
    if (req.isAuthenticated()) {
      return next()
    }
  
    res.redirect('/SignIn')
  }
  
  function checkNotAuthenticated(req, res, next) {
    if (req.isAuthenticated()) {
      return res.redirect('/')
    }
    next()
  }
  
// Start the server
const PORT = process.env.PORT || 5500;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});