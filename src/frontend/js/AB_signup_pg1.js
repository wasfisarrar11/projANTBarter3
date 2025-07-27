const signInForm = document.getElementById("signIn-form");
const signInButton = document.getElementById("signIn-form-submit");
const signInErrorMsg = document.getElementById("signIn-error-msg");

const termsCheckbox = document.getElementById("agree");

// Add event listener to the "Sign Up" button
signInButton.addEventListener("click", (e) => {
  // Validate the form before submitting
  if (!signInForm.reportValidity()) {
    return;
  }

  // Display a confirmation message
  alert("Thank you for signing up! Please check your email to verify your account.");

  // Redirect to the homepage after a delay of 3 seconds
  setTimeout(function () {
    window.location.href = "AB_Home_UI.html";
  }, 3000);
});