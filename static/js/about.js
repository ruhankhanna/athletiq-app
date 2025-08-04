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

document.addEventListener('DOMContentLoaded', function () {
  const reveals = document.querySelectorAll('.reveal');

  function revealOnScroll() {
    const windowHeight = window.innerHeight;
    const revealPoint = 150;

    reveals.forEach(el => {
      const top = el.getBoundingClientRect().top;
      if (top < windowHeight - revealPoint) {
        el.classList.add('visible');
      }
    });
  }

  window.addEventListener('scroll', revealOnScroll);
  revealOnScroll();
});
