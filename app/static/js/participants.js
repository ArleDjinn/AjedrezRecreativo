document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("participant-count");
  const container = document.getElementById("participants-container");
  const prefill = window.__participants_prefill__ || [];

  function render(n) {
    container.innerHTML = "";
    for (let i = 0; i < n; i++) {
      const p = prefill[i] || {};
      const block = document.createElement("div");
      block.style.border = "1px solid #ddd";
      block.style.padding = "0.75rem";
      block.style.marginBottom = "0.75rem";

      block.innerHTML = `
        <strong>Participante #${i + 1}</strong><br><br>

        <label>Nombre</label><br>
        <input name="participant_name_${i}" value="${(p.name || "").replace(/"/g, "&quot;")}" required><br><br>

        <label>Edad</label><br>
        <input type="number" name="participant_age_${i}" min="1" max="120" value="${p.age ?? ""}" required>
      `;
      container.appendChild(block);
    }
  }

  function currentN() {
    return parseInt(select.value, 10) || 1;
  }

  select.addEventListener("change", () => render(currentN()));
  render(currentN());
});
