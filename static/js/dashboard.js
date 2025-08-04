



document.addEventListener('DOMContentLoaded', function () {
    const menuButton = document.querySelector('.menu-button');
    const menuContent = document.querySelector('.menu-content');

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




function openSettingsModal() {
  document.getElementById("settings-modal").style.display = "flex";
}
function closeSettingsModal() {
  document.getElementById("settings-modal").style.display = "none";
}

// Optional: Close on outside click
window.addEventListener("click", function (e) {
  if (e.target.classList.contains("modal")) {
    e.target.style.display = "none";
  }
});


document.addEventListener('DOMContentLoaded', function () {
  let visibleCount = 4;
  const increment = 4;
  const resultItems = Array.from(document.querySelectorAll(".recent-results-item"));
  const loadMoreButton = document.getElementById("load-more-button");

  if (loadMoreButton && resultItems.length > visibleCount) {
    loadMoreButton.style.display = "block";
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

// FILTER FUNCTIONALITY
document.addEventListener("DOMContentLoaded", () => {
  const yearFilter = document.getElementById("year-filter");
  const eventFilter = document.getElementById("event-filter");
  const results = document.querySelectorAll(".recent-results-item");
  const loadMoreBtn = document.getElementById("load-more-button");

  function applyFilters() {
  const selectedYear = yearFilter.value;    // e.g. "2024" or ""
  const selectedEvent = eventFilter.value;  // e.g. "100M" or ""
  const allResults = Array.from(results);

  // Filter by year and event
  const matchedResults = allResults.filter(result => {
    const rawDate = result.getAttribute("data-year");   // e.g. "2024-05-14"
    const resultYear = rawDate.slice(0, 4);             // "2024"
    const resultEvent = result.getAttribute("data-event");
    
    const matchYear  = !selectedYear  || resultYear  === selectedYear;
    const matchEvent = !selectedEvent || resultEvent === selectedEvent;
    return matchYear && matchEvent;
  });

  // Hide everything, then show up to the first 4 matches
  allResults.forEach(r => r.classList.add("hidden-result"));
  matchedResults.slice(0, 4).forEach(r => r.classList.remove("hidden-result"));

  // Reset & toggle Load More button
  if (matchedResults.length > 4) {
    loadMoreBtn.style.display = "block";
    loadMoreBtn.dataset.visibleCount = 4;
  } else {
    loadMoreBtn.style.display = "none";
  }
}



  function loadMoreFilteredResults() {
  const selectedYear = yearFilter.value;
  const selectedEvent = eventFilter.value;

  let matchedResults = Array.from(results).filter(result => {
    const resultYear = result.getAttribute("data-year");
    const resultEvent = result.getAttribute("data-event");

    const matchYear = !selectedYear || resultYear === selectedYear;
    const matchEvent = !selectedEvent || resultEvent === selectedEvent;

    return matchYear && matchEvent;
  });

  let currentlyVisible = parseInt(loadMoreBtn.dataset.visibleCount || 4);
  const increment = 4;
  const newVisibleCount = currentlyVisible + increment;

  matchedResults.slice(currentlyVisible, newVisibleCount).forEach(result => result.classList.remove("hidden-result"));

  loadMoreBtn.dataset.visibleCount = newVisibleCount;

  if (newVisibleCount >= matchedResults.length) {
    loadMoreBtn.style.display = "none";
  }
}


yearFilter.addEventListener("change", applyFilters);
eventFilter.addEventListener("change", applyFilters);
loadMoreBtn.addEventListener("click", loadMoreFilteredResults);

applyFilters(); // Execute initially

});
