// static/js/file-upload.js

document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector(".upload-form");
    if (!form) {
        return;
    }

    const fileInput = document.querySelector("input[type='file']");
    const submitBtn = form.querySelector("button[type='submit']");
    const maxSizeMb = Number(form.dataset.maxSizeMb || 100);

    // Show selected file name
    if (fileInput) {
        fileInput.addEventListener("change", function () {
            if (fileInput.files.length > 0) {
                const fileName = fileInput.files[0].name;
                const label = fileInput.previousElementSibling;
                label.textContent = `Selected File: ${fileName}`;
            }
        });
    }

    // Match the server-side upload limit.
    form.addEventListener("submit", function (event) {
        if (fileInput.files.length > 0) {
            const fileSize = fileInput.files[0].size / (1024 * 1024); // in MB
            if (fileSize > maxSizeMb) {
                event.preventDefault();
                alert(`File size exceeds ${maxSizeMb} MB. Please choose a smaller file.`);
                return false;
            }
        }
        // Add loading state
        submitBtn.disabled = true;
        submitBtn.textContent = "Uploading...";
    });
});
