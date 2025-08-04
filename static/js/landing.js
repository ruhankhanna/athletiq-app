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

    // === Scroll Reveal Animation ===
    function revealOnScroll() {
        const reveals = document.querySelectorAll('.reveal');
        const windowHeight = window.innerHeight;
        const revealPoint = 150;

        reveals.forEach(el => {
            const elementTop = el.getBoundingClientRect().top;
            if (elementTop < windowHeight - revealPoint) {
                el.classList.add('visible');
            }
        });
    }

    window.addEventListener('scroll', revealOnScroll);
    revealOnScroll(); // Trigger on load in case elements are already in view
});


document.addEventListener('DOMContentLoaded', function () {
  const arrow = document.querySelector('.scroll-down-arrow');
  if (arrow) {
    arrow.addEventListener('click', function () {
      window.scrollBy({
        top: window.innerHeight * 0.9,
        left: 0,
        behavior: 'smooth'
      });
    });
  }
});


