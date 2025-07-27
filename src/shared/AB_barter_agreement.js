// Function to construct PDF content based on form data
function constructPdfContent() {
  // Get the data from the form fields
  const barterType = document.querySelector('input[name="barterType"]:checked').value;
  const partyA = document.getElementById("partyA").value;
  const partyA_offer = document.getElementById(`partyA_offer_${barterType}`).value;
  const partyB = document.getElementById("partyB").value;
  const partyB_offer = document.getElementById(`partyB_offer_${barterType}`).value;
  const startDate = document.getElementById("startDate").value;
  const endDate = document.getElementById("endDate").value;
  const additionalTerms = document.getElementById("additionalTerms").value;

  // Log the values to the console
  console.log("Barter Type:", barterType);
  console.log("Party A:", partyA);
  console.log("Party A's Offer:", partyA_offer);
  console.log("Party B:", partyB);
  console.log("Party B's Offer:", partyB_offer);
  console.log("Start Date:", startDate);
  console.log("End Date:", endDate);
  console.log("Additional Terms:", additionalTerms);
  
  // Construct the content for the PDF
  const content = `
    <h1>Barter Agreement</h1>
    <p><strong>Barter Type:</strong> ${barterType}</p>
    <p><strong>Party A:</strong> ${partyA}</p>
    <p><strong>Party A's Offering (${barterType}):</strong> ${partyA_offer}</p>
    <p><strong>Party B:</strong> ${partyB}</p>
    <p><strong>Party B's Offering (${barterType}):</strong> ${partyB_offer}</p>
    <p><strong>Start Date:</strong> ${startDate}</p>
    <p><strong>End Date:</strong> ${endDate}</p>
    <p><strong>Additional Terms:</strong></p>
    <p>${additionalTerms}</p>
  `;

  return content;
}

// Generate a PDF document based on the data entered in the barter agreement form fields
const printPdf = async () => {
  console.log("Generating PDF...");
  try {
    // Construct the filename dynamically
    const partyA = document.getElementById("partyA").value;
    const partyB = document.getElementById("partyB").value;
    const filename = `BarterAgreement_Template_${partyA}_${partyB}.pdf`;

    // Construct the content for the PDF
    const content = constructPdfContent();

    console.log("Content:", content);

    const opt = {
      margin: 1,
      filename: filename,
      image: { type: "png", quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { unit: "in", format: "letter", orientation: "portrait" },
    };
    
    // Generate the PDF using html2pdf
    const element = document.createElement("div");
    element.innerHTML = content;
    document.body.appendChild(element); // Add the element to the DOM
    
    await html2pdf().from(element).set(opt).save();
    document.body.removeChild(element); // Remove the element from the DOM after the PDF has been generated
    
    console.log("PDF generated successfully.");
  } catch (error) {
    console.error("Error generating PDF:", error);
    }
};

// Validate and save PDF function
function validateAndSavePdf() {
  // Define the required fields based on the selected barterType
  const barterType = document.querySelector('input[name="barterType"]:checked').value;
  let requiredFields = ['partyA', 'partyB', 'startDate', 'endDate', 'additionalTerms'];

  // Add appropriate offer fields based on the selected barterType
  if (barterType === 'oneTime') {
    requiredFields.push('partyA_offer_oneTime', 'partyB_offer_oneTime');
  } else {
    requiredFields.push('partyA_offer_ongoing', 'partyB_offer_ongoing');
  }

  // Check if any required field is empty
  let emptyFields = [];
  requiredFields.forEach(field => {
    const value = document.getElementById(field).value.trim();
    if (!value) {
      emptyFields.push(field);
    }
  });

  // Filter out irrelevant offer fields based on the selected barterType
  if (barterType === 'oneTime') {
    emptyFields = emptyFields.filter(field => !['partyA_offer_ongoing', 'partyB_offer_ongoing'].includes(field));
  } else {
    emptyFields = emptyFields.filter(field => !['partyA_offer_oneTime', 'partyB_offer_oneTime'].includes(field));
  }

  if (emptyFields.length > 0) {
    // Display error message listing incomplete fields
    const errorMessage = `Please fill out the following fields: ${emptyFields.join(', ')}.`;
    document.getElementById('error-message').textContent = errorMessage;
  } else {
    // If all required fields are filled out, save the PDF
    printPdf(); // Move printPdf function call here
  }
}

function handleSavePdfButtonClick() {
  // Prompt user with a confirmation dialog before saving the PDF
  const confirmed = confirm('Are you sure you want to save the PDF?');

  if (confirmed) {
    // If user confirms, call the validateAndSavePdf function
    validateAndSavePdf();
  }
}