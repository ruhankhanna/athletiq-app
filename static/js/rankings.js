document.addEventListener("DOMContentLoaded", () => {
  // initialize: mark first gender of each event as active
  document.querySelectorAll(".rankings-event-section").forEach(section => {
    const firstTab = section.querySelector(".gender-tab");
    const event = firstTab.dataset.event;
    const gender = firstTab.dataset.gender;

    // activate first tab
    firstTab.classList.add("active");
    // show matching table
    section.querySelector(`.rankings-table[data-event="${event}"][data-gender="${gender}"]`)
           .classList.add("active");

    // hook up clicks
    section.querySelectorAll(".gender-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        // deactivate all tabs + tables
        section.querySelectorAll(".gender-tab").forEach(t => t.classList.remove("active"));
        section.querySelectorAll(".rankings-table").forEach(tbl => tbl.classList.remove("active"));

        // activate clicked
        tab.classList.add("active");
        const e = tab.dataset.event, g = tab.dataset.gender;
        section.querySelector(`.rankings-table[data-event="${e}"][data-gender="${g}"]`)
               .classList.add("active");
      });
    });
  });
});
