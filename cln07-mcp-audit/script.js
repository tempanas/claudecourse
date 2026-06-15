"use strict";

const form = document.querySelector("#consultation-form");
const successMessage = document.querySelector("#success-message");
const closeMessageButton = document.querySelector(".message-close");

function setFieldState(field, isValid) {
  const wrapper = field.closest(".field");
  wrapper.classList.toggle("is-invalid", !isValid);
  field.setAttribute("aria-invalid", String(!isValid));
}

function validateField(field) {
  const isValid = field.value.trim() !== "";
  setFieldState(field, isValid);
  return isValid;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  successMessage.hidden = true;

  const requiredFields = [...form.querySelectorAll("[required]")];
  const isFormValid = requiredFields.map(validateField).every(Boolean);

  if (!isFormValid) {
    const firstInvalidField = form.querySelector(".is-invalid input, .is-invalid select, .is-invalid textarea");
    firstInvalidField?.focus();
    return;
  }

  successMessage.hidden = false;
  successMessage.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

form.addEventListener("input", (event) => {
  if (event.target.matches("[required]") && event.target.value.trim() !== "") {
    setFieldState(event.target, true);
  }
});

form.addEventListener("change", (event) => {
  if (event.target.matches("select[required]")) {
    validateField(event.target);
  }
});

closeMessageButton.addEventListener("click", () => {
  successMessage.hidden = true;
});
