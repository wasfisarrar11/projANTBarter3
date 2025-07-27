const form = document.querySelector('form');

if (form) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    // Disable form submission button to prevent multiple submissions
    const submitButton = form.querySelector('[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
    }

    // Get form data
    const formData = new FormData(form);

    // Send form data to server
    fetch('https://example.com/submit-posting', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      // Enable form submission button
      if (submitButton) {
        submitButton.disabled = false;
      }

      // Handle response
      if (!response.ok) {
        throw new Error('Error submitting form');
      }
      return response.json();
    })
    .then(data => {
      // Handle successful response
      console.log(data);
      // Redirect to confirmation page or show success message
      alert('Submission successful!');
      form.reset();
    })
    .catch(error => {
      // Enable form submission button
      if (submitButton) {
        submitButton.disabled = false;
      }

      // Handle error
      console.error(error);
      // Show error message
      alert('Submission failed. Please try again later.');
    });
  });
}