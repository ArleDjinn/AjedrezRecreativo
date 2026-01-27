document.addEventListener("DOMContentLoaded", () => {
  const ageInput = document.querySelector('input[name="participant_age"]');
  const guardianSection = document.getElementById('guardian-section');
  const adultSection = document.getElementById('adult-section');

  function toggleSections() {
    if (!ageInput || !guardianSection || !adultSection) return;

    const age = parseInt(ageInput.value, 10);

    if (Number.isNaN(age)) {
      guardianSection.style.display = 'none';
      adultSection.style.display = 'none';
      return;
    }

    if (age < 18) {
      guardianSection.style.display = 'block';
      adultSection.style.display = 'none';
    } else {
      guardianSection.style.display = 'none';
      adultSection.style.display = 'block';
    }
  }

  if (ageInput) {
    ageInput.addEventListener('input', toggleSections);
    ageInput.addEventListener('change', toggleSections);
    toggleSections(); // <-- CLAVE
  }
});