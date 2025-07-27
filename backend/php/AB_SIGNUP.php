<?php

$host = 'a9b72ee816d64ca751459a1171836a83.c9iwyumu4w7q.us-west-2.rds.amazonaws.com';  
$dbname = 'newab';
$username = 'dbmasteruser';
$password = 'Wasfiothman1';


$conn = new mysqli($host, $username, $password, $dbname);


if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

$stmt = $conn->prepare("INSERT INTO user (First_Name, Last_Name, Email, Birthday, Password, Phone_Number) 
                        VALUES (?, ?, ?, STR_TO_DATE(?, '%Y-%m-%d'), ?, ?)");
$stmt->bind_param("ssssss", $firstName, $lastName, $email, $birthday, $hashedPassword, $phoneNumber);


$firstName = $_POST['fName'];
$lastName = $_POST['lName'];
$email = $_POST['email'];
$birthday = $_POST['bdate'];
$rawPassword = $_POST['password'];
$phoneNumber = $_POST['pNum'];

$hashedPassword = password_hash($rawPassword, PASSWORD_DEFAULT);

$stmt->execute();

echo "New record created successfully";

if ($stmt->affected_rows > 0) {
    echo "New record created successfully";
} else {
    echo "Error: " . $stmt->error;
}
$stmt->close();
$stmt->close();
?>
