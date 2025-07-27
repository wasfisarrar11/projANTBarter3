<?php
$host = "ls-5a1a450da9b72ee816d64ca751459a1171836a83.c9iwyumu4w7q.us-west-2.rds.amazonaws.com";
$port = 3306;
$socket = "";
$user = "dbmasteruser";
$password = "";
$dbname = "newab";

$con = new mysqli($host, $user, $password, $dbname, $port, $socket);

if ($con->connect_error) {
    die("Connection failed: ". $con->connect_error);
}

// Escape user inputs for security to prevent SQL injection
$firstName = $_POST['FirstName'];
$lastName = $_POST['LastName'];
$email = $_POST['Email'];
$bday = $_POST['Birthday'];
$password = password_hash($_POST['Password'], PASSWORD_DEFAULT); // Hash the password before storing
$phoneNumber = $_POST['PhoneNumber'];

// Prepare and bind
$stmt = $con->prepare("INSERT INTO users (FirstName, LastName, Email, Birthday, Password, PhoneNumber) VALUES (?,?,?,?,?,?)");
$stmt->bind_param("ssssss", $firstName, $lastName, $email, $bday, $password, $phoneNumber);

// Set parameters and execute
$firstName = mysqli_real_escape_string($con, $FirstName);
$lastName = mysqli_real_escape_string($con, $LastName);
$email = mysqli_real_escape_string($con, $Email);
$bday = mysqli_real_escape_string($con, $Birthday);
$phoneNumber = mysqli_real_escape_string($con, $PhoneNumber);

$stmt->execute();

if ($stmt->affected_rows > 0) {
    echo "New record created successfully";
} else {
    echo "Error: ". $stmt->error;
}

// Close statement and connection
$stmt->close();
$con->close();
?>
