document.addEventListener('DOMContentLoaded', function () {
  // Menu toggle code stays unchanged
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

  // Scroll to bottom reliably
  const messagesBox = document.querySelector('.messages-box');
  if (messagesBox) {
    // Defer until messages have likely rendered
    requestAnimationFrame(() => {
      setTimeout(() => {
        messagesBox.scrollTop = messagesBox.scrollHeight;
      }, 100); // You can increase to 200ms if still not working
    });
  }
});
