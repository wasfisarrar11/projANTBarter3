<?php
// Example in PHP using password_hash and password_verify functions

$password = 'Password'; // Password input from the user

// Hashing the password with a salt (automatically generated)
$hashedPassword = password_hash($password, PASSWORD_DEFAULT);

// Storing the $hashedPassword in your MySQL database instead of the plain text password

// To verify the password when the user logs in
$password = 'Password'; // Password input during login

if (password_verify($password, $hashedPassword)) {
    echo 'Password is valid!';
} else {
    echo 'Invalid password.';
}
?>
