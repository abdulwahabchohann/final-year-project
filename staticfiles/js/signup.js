// signup.js

// DOM references
const form = document.getElementById("signup-form");
const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirm-password");

// ✅ 1. Live Password Strength Checker
password.addEventListener("input", () => {
    const strength = getPasswordStrength(password.value);
    confirmPassword.setCustomValidity(""); // reset validity

    if (strength === "weak") {
        password.style.borderColor = "red";
    } else if (strength === "medium") {
        password.style.borderColor = "orange";
    } else {
        password.style.borderColor = "green";
    }
});

// Password strength calculator
function getPasswordStrength(pass) {
    let strength = 0;
    if (pass.length >= 8) strength++;
    if (/[A-Z]/.test(pass)) strength++;
    if (/[0-9]/.test(pass)) strength++;
    if (/[\W]/.test(pass)) strength++;

    if (strength <= 1) return "weak";
    else if (strength === 2 || strength === 3) return "medium";
    else return "strong";
}

// ✅ 2. Password Match Validation
confirmPassword.addEventListener("input", () => {
    if (confirmPassword.value !== password.value) {
        confirmPassword.setCustomValidity("Passwords do not match!");
    } else {
        confirmPassword.setCustomValidity("");
    }
});

// ✅ 3. AJAX Form Submit
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        password: password.value,
        confirm_password: confirmPassword.value
    };

    try {
        const response = await fetch("/signup-api/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken() // Django security
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            alert("✅ Signup Successful!");
            form.reset();
        } else {
            alert("❌ Error: " + (result.message || "Something went wrong."));
        }
    } catch (err) {
        console.error("AJAX error:", err);
        alert("❌ Failed to send data.");
    }
});

// Helper function to get Django CSRF token from cookie
function getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}
