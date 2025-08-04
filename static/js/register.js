document.addEventListener('DOMContentLoaded', function() {
            var birthdayInput = document.getElementById('birthday');
            birthdayInput.placeholder = 'BIRTHDAY';
        });


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
  const toggle = document.getElementById('togglePassword');
  const password = document.getElementById('password');

  if (toggle && password) {
    toggle.addEventListener('click', function () {
      const isPassword = password.getAttribute('type') === 'password';
      password.setAttribute('type', isPassword ? 'text' : 'password');
      toggle.classList.toggle('fa-eye');
      toggle.classList.toggle('fa-eye-slash');
    });
  }
});




document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector(".register-form");
  const overlay = document.getElementById("loadingOverlay");

  if (form && overlay) {
    form.addEventListener("submit", () => {
      overlay.style.display = "flex";
    });
  }
});



document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".register-form");

  form.addEventListener("submit", function (e) {
    const state = form.state.value.trim().toUpperCase();
    const gradYear = form.grad_year.value.trim();
    const password = form.password.value;

    if (state && !/^[A-Z]{2}$/.test(state)) {
      alert("Please enter a valid 2-letter state abbreviation.");
      e.preventDefault();
    }

    if (gradYear && !/^\d{4}$/.test(gradYear)) {
      alert("Graduation year must be 4 digits.");
      e.preventDefault();
    }

    if (password.length < 8) {
      alert("Password must be at least 8 characters.");
      e.preventDefault();
    }
  });
});


document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".register-form");
  const schoolInput = document.getElementById("school");
  const gradYearInput = document.getElementById("grad_year");

  form.addEventListener("submit", function (e) {
    const schoolFilled = schoolInput.value.trim() !== "";
    const gradYearFilled = gradYearInput.value.trim() !== "";

    if ((schoolFilled && !gradYearFilled) || (!schoolFilled && gradYearFilled)) {
      e.preventDefault();
      alert("If you provide a school, you must also provide a graduation year — and vice versa.");
    }
  });
});
