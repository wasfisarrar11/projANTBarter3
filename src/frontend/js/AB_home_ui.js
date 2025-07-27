// Navigation handling
var navLinks = document.querySelectorAll("nav a");
navLinks.forEach(function (link) {
  link.addEventListener("click", function (e) {
    e.preventDefault();

    // Hide all sections
    document.querySelectorAll(".content-page").forEach(function (page) {
      page.classList.remove("active");
    });

    // Show clicked section
    var target = e.target.getAttribute("data-target");
    document.getElementById(target).classList.add("active");
  });
});

// Basic pop-up for Sign In and Sign Up
document.getElementById("signIn").addEventListener("click", function () {
  window.location.href = "AB_SignIn.html";
});

document.getElementById("signUp").addEventListener("click", function () {
  window.location.href = "AB_SignUp_pg1.html";
});
// Basic model for Sign In and Sign Up
function showModal(title) {
  let modal = document.createElement("div");
  modal.style.position = "fixed";
  modal.style.top = "0";
  modal.style.left = "0";
  modal.style.width = "100vw";
  modal.style.height = "100vh";
  modal.style.backgroundColor = "rgba(0,0,0,0.7)";
  modal.style.display = "flex";
  modal.style.justifyContent = "center";
  modal.style.alignItems = "center";

  let modalContent = document.createElement("div");
  modalContent.style.backgroundColor = "white";
  modalContent.style.padding = "20px";
  modalContent.style.borderRadius = "10px";

  let closeBtn = document.createElement("button");
  closeBtn.innerHTML = "Close";
  closeBtn.addEventListener("click", function () {
    document.body.removeChild(modal);
  });
}

document.getElementById("signIn").addEventListener("click", function () {
  showModal("Sign In");
});

document.getElementById("signUp").addEventListener("click", function () {
  showModal("Sign Up");
});