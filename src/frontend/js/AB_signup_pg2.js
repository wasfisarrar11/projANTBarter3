// Function to check if passwords match
const checkPasswordMatch = () => {
  const passwordInput = document.getElementById('Password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const confirmPasswordError = document.querySelector('.confirm-password-error');
  const confirmPasswordSuccess = document.querySelector('.confirm-password-success');

  if (passwordInput.value !== confirmPasswordInput.value) {
    confirmPasswordError.classList.remove('hidden');
    confirmPasswordError.classList.add('opacity-100');
    confirmPasswordSuccess.classList.remove('opacity-100');
    confirmPasswordSuccess.classList.add('hidden');
  } else {
    confirmPasswordError.classList.remove('opacity-100');
    confirmPasswordError.classList.add('hidden');
    confirmPasswordSuccess.classList.remove('hidden');
    confirmPasswordSuccess.classList.add('opacity-100');
  }
};

// Add event listeners for input and blur events on password and confirm password fields
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form[name="user_sign_up"]');
  const confirmPasswordInput = form.querySelector('#confirmPassword');
  confirmPasswordInput.addEventListener('input', checkPasswordMatch);
  confirmPasswordInput.addEventListener('blur', checkPasswordMatch);
});

// Added an event listener that checks the password match before the form is submitted
document.addEventListener('DOMContentLoaded', function () {
  // Add a submit event listener to the form
  const form = document.querySelector('form[name="user_sign_up"]');
  form.addEventListener('submit', function (event) {
    const passwordInput = document.getElementById('Password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const confirmPasswordError = document.querySelector('.confirm-password-error');
    const confirmPasswordSuccess = document.querySelector('.confirm-password-success');

    // If the passwords don't match, show the error message and prevent form submission
    if (passwordInput.value !== confirmPasswordInput.value) {
      confirmPasswordError.classList.remove('hidden');
      confirmPasswordError.classList.add('opacity-100', 'pointer-events-auto');
      confirmPasswordSuccess.classList.remove('opacity-100', 'pointer-events-auto');
      confirmPasswordSuccess.classList.add('hidden');
      event.preventDefault(); // Prevent form submission here 
    }
    
    // If the passwords match, clear the error message and allow form submission
    else {
      confirmPasswordError.classList.remove('opacity-100', 'pointer-events-auto');
      confirmPasswordError.classList.add('hidden');
      confirmPasswordSuccess.classList.remove('hidden');
      confirmPasswordSuccess.classList.add('opacity-100', 'pointer-events-auto');
    }

  });
});

// Validate that the form works as expected
const validateForm = (formSelector) => {
  const formElement = document.getElementById(formSelector);
  let error = 0;

  const validationOptions = [
    {
      attribute: 'minlength',
      isValid: input => input.value && input.value.length >= parseInt(input.minLength, 10),
      errorMessage: (input, label) => `${label.textContent} needs to be at least ${input.minLength} characters`,
    },
    {
      attribute: 'pattern',
      isValid: input => {
        const patternRegex = new RegExp(input.pattern);
        return patternRegex.test(input.value);
      },
      errorMessage: (input, label) => `${label.textContent} should be a valid email`,
    },
    {
      attribute: 'required',
      isValid: input => input.value.trim() !== '',
      errorMessage: (input, label) => `${label.textContent} is required`,
    },
    {
      attribute: 'match-password',
      isValid: input => {
        const matchPassword = formElement.querySelector(`input[match-password="${input.id}"]`);
        return matchPassword && matchPassword.value === input.value;
      },
      errorMessage: (input, label) => `Passwords do not match`,
    },
    {
      attribute: 'confirm-password',
      isValid: (input, formElement) => {
        const passwordInput = formElement.querySelector('input[type="Password"]');
        return passwordInput && input.value === passwordInput.value;
      },
      errorMessage: (input, label) => `Passwords do not match`,
    },
  ];

  // Call the checkPasswordMatch function with the form element
  checkPasswordMatch(formElement);

  const validateSingleFormGroup = (formGroup, formElement) => {
    const label = formGroup.querySelector('label');
    const input = formGroup.querySelector('input, textarea');
    const errorContainer = formGroup.querySelector('.error');
    const errorIcon = formGroup.querySelector('.error-icon');
    const successIcon = formGroup.querySelector('.success-icon');
    
    // Check if the password match validation is needed
    if (input.hasAttribute('match-password') || input.hasAttribute('confirm-password')) {
      checkPasswordMatch(formElement);
    }

    let formGroupError = false;
    for (const option of validationOptions) {
      if (input.hasAttribute(option.attribute) && !option.isValid(input)) {
        errorContainer.textContent = option.errorMessage(input, label);
        input.classList.add('border-red-700');
        input.classList.remove('border-green-700');
        successIcon.classList.add('hidden');
        errorIcon.classList.remove('hidden');

        // Check if the error is due to the password match validation
        if (input.hasAttribute('match-password')) {
          input.classList.add('bg-red-100');
        }

        formGroupError = true;
        break;
      }
    }

    if (!formGroupError) {
      errorContainer.textContent = '';
      input.classList.add('border-green-700');
      input.classList.remove('border-red-700');
      successIcon.classList.remove('hidden');
      errorIcon.classList.add('hidden');

      // If the input is the confirm password, remove the red bg-color
      if (input.hasAttribute('confirm-password')){
        input.classList.add('border-green-700');
        input.classList.remove('bg-red-100', 'bg-green-100');
      }
    }
  };

  const validateAllFormGroups = () => {
    const formGroups = Array.from(formElement.querySelectorAll('.formGroup'));
    formGroups.forEach(formGroup => {
      validateSingleFormGroup(formGroup, formElement);
    });
  }

  // Disable HTML5 Validation
  formElement.setAttribute('novalidate', '');

  // Enable validation for each control whilst updating form
  Array.from(formElement.elements).forEach(element =>
    element.addEventListener('blur', event => {
      if (['Password', 'confirm-password'].includes(event.srcElement.id)) {
        const passwordInput = formElement.querySelector('input[type="Password"]');
        const confirmPasswordInput = formElement.querySelector('input[match-password]');
  
        if (passwordInput.value !== confirmPasswordInput.value) {
          const confirmPasswordFormGroup = confirmPasswordInput.parentElement.parentElement;
          const confirmPasswordErrorContainer = confirmPasswordFormGroup.querySelector('.error');
          confirmPasswordErrorContainer.textContent = 'Passwords do not match';
          confirmPasswordInput.classList.add('border-red-700');
          confirmPasswordInput.classList.remove('border-green-700');
        }
      }
  
      validateSingleFormGroup(event.srcElement.parentElement.parentElement);
    })
  );

  const eventListeners = () => {
    const formElement = document.querySelector(formSelector);
  
    // Add the input event listener for both password and confirm password fields
    formElement.addEventListener('input', (event) => {
      if (event.target.type === 'Password' || event.target.id === 'confirmPassword') {
        validateSingleFormGroup(event.target.parentElement.parentElement);
      }
    });
  
    // Add the rest of the existing event listeners
    formElement.addEventListener('submit', validateOnSubmit);
    formElement.querySelector('input[type="submit"]').addEventListener('click', (event) => event.stopPropagation());
    Array.from(formElement.elements).forEach(element => {
      element.addEventListener('blur', validateBlur);
      if (element.type !== 'submit') {
        element.addEventListener('input', validateOnInput);
      }
    });
  
    // Add the check validation after the form is rendered
    setTimeout(validateAllFormGroups, 100);
  };
  eventListeners();

  // Only validate form when submitting
  formElement.addEventListener('submit', event => {
    event.preventDefault();
    validateAllFormGroups();

    if (error === 0) {
      // Check if passwords match      
      const passwordInput = formElement.querySelector('input[type="Password"]');
      const confirmPasswordInput = formElement.querySelector('input[match-password]');
      if (passwordInput.value !== confirmPasswordInput.value) {
        const confirmPasswordFormGroup = confirmPasswordInput.parentElement.parentElement;
        const confirmPasswordErrorContainer = confirmPasswordFormGroup.querySelector('.error');
        confirmPasswordErrorContainer.textContent = 'Passwords do not match';
        confirmPasswordInput.classList.add('border-red-700');
        confirmPasswordInput.classList.remove('border-green-700');
        error++;
      }

      if (error === 0) {
        // Proceed with form submission
        // You can add your submission logic here
        const formData = new FormData(formElement);
        // Example: Fetch request to submit form data
        fetch(formElement.action, {
          method: formElement.method,
          body: formData
        })
        .then(response => {
          if (response.ok) {
            // Handle successful form submission
            console.log('Form submitted successfully');
            // Optionally, you can redirect the user to another page
            window.location.href = 'success.html';
          } else {
            // Handle form submission failure
            console.error('Form submission failed');
          }
        })
        .catch(error => {
          console.error('Error submitting form:', error);
        });
      } else {
        // There are errors in the form, do not submit
        console.log('Form has errors. Please correct them.');
      }
    }
  });
};

// Call validateForm function with the form selector
validateForm('form[name="user_sign_up"]');