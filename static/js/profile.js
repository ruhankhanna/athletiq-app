document.addEventListener('DOMContentLoaded', function () {
  const menuButton = document.querySelector('.menu-button');
  const menuContent = document.querySelector('.menu-content');
  const messageBox = document.querySelector(".message-box");

  if (menuButton && menuContent) {
    menuButton.addEventListener('click', function (event) {
      event.stopPropagation();
      menuContent.classList.toggle('active');
    });

    document.addEventListener('click', function (event) {
      if (!menuButton.contains(event.target) && !menuContent.contains(event.target)) {
        menuContent.classList.remove('active');
      }
    });
  } else {
    console.warn("Menu button or menu content not found.");
  }

  if (messageBox) {
    messageBox.scrollTop = messageBox.scrollHeight;
  }

  // ✅ Load More Functionality
  let visibleCount = 4;
  const increment = 4;
  const resultItems = Array.from(document.querySelectorAll(".recent-results-item"));
  const loadMoreButton = document.getElementById("load-more-button");

  if (loadMoreButton && resultItems.length > visibleCount) {
    loadMoreButton.style.display = "block"; // show it if needed
    loadMoreButton.addEventListener("click", function () {
      visibleCount += increment;

      resultItems.forEach((item, index) => {
        if (index < visibleCount) {
          item.classList.remove("hidden-result");
        }
      });

      if (visibleCount >= resultItems.length) {
        loadMoreButton.style.display = "none";
      }
    });
  }
});


function showInfo(el) {
  const event = el.getAttribute("data-event");
  const popup = document.getElementById("infoPopup");
  const text = document.getElementById("infoText");

  if (event === "1 Mile") {
    text.textContent = "This rating incorporates 1500M and 1600M times.";
  } else if (event === "2 Mile") {
    text.textContent = "This rating incorporates 3000M and 3200M times.";
  } else {
    text.textContent = "";
  }

  popup.style.display = "flex";
}

function closeInfo() {
  document.getElementById("infoPopup").style.display = "none";
}



// FILTER FUNCTIONALITY
// FILTER FUNCTIONALITY
document.addEventListener("DOMContentLoaded", () => {
  const yearFilter   = document.getElementById("year-filter");
  const eventFilter  = document.getElementById("event-filter");
  const results      = Array.from(document.querySelectorAll(".recent-results-item"));
  const loadMoreBtn  = document.getElementById("load-more-button");

  function applyFilters() {
    const selectedYear  = yearFilter.value;    // e.g. "2024" or ""
    const selectedEvent = eventFilter.value;   // e.g. "100M" or ""
    let shownCount = 0;

    // First, hide all
    results.forEach(r => r.classList.add("hidden-result"));

    // Then, for each matching item, show up to 4
    results.forEach(r => {
      const rawDate    = r.getAttribute("data-year");   // "2024-05-14"
      const resultYear = rawDate.slice(0, 4);           // "2024"
      const resultEvent= r.getAttribute("data-event");

      const matchYear  = !selectedYear  || resultYear  === selectedYear;
      const matchEvent = !selectedEvent || resultEvent === selectedEvent;

      if (matchYear && matchEvent && shownCount < 4) {
        r.classList.remove("hidden-result");
        shownCount++;
      }
    });

    // Show/hide Load More
    // Are there still hidden matches?
    const moreToShow = results.some(r => {
      const rawDate    = r.getAttribute("data-year").slice(0,4);
      const resultEvent= r.getAttribute("data-event");
      const matchYear  = !selectedYear  || rawDate    === selectedYear;
      const matchEvent = !selectedEvent || resultEvent === selectedEvent;
      return matchYear && matchEvent && r.classList.contains("hidden-result");
    });

    loadMoreBtn.style.display = moreToShow ? "block" : "none";
  }

  function loadMoreFilteredResults() {
    const selectedYear  = yearFilter.value;
    const selectedEvent = eventFilter.value;

    // Just reveal all that match
    results.forEach(r => {
      const rawDate    = r.getAttribute("data-year").slice(0,4);
      const resultEvent= r.getAttribute("data-event");

      const matchYear  = !selectedYear  || rawDate    === selectedYear;
      const matchEvent = !selectedEvent || resultEvent === selectedEvent;

      if (matchYear && matchEvent) {
        r.classList.remove("hidden-result");
      }
    });

    loadMoreBtn.style.display = "none";
  }

  yearFilter.addEventListener("change", applyFilters);
  eventFilter.addEventListener("change", applyFilters);
  loadMoreBtn.addEventListener("click", loadMoreFilteredResults);

  applyFilters();  // initial run
});

