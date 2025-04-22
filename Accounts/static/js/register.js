document.addEventListener('DOMContentLoaded', function() {
    const usernameInput = document.getElementById('username');
    const usernameStatus = document.createElement('div');
    usernameStatus.className = 'username-status';
    usernameInput.parentNode.appendChild(usernameStatus);

    let debounceTimer;

    function validateUsername(username) {
        // Pattern validation rule for username not starting with numbers
        const pattern = /^[A-Za-z][A-Za-z0-9_]{2,19}$/;
        
        if (!pattern.test(username)) {
            return { valid: false, message: 'Username must start with a letter and be 3-20 characters long, containing only letters, numbers, and underscores' };
        }
        return { valid: true };
    }

    function checkUsername(username) {
        // First perform client-side validation
        const validation = validateUsername(username);
        if (!validation.valid) {
            usernameStatus.textContent = validation.message;
            usernameStatus.className = 'username-status error';
            usernameInput.classList.remove('valid');
            usernameInput.classList.add('invalid');
            return;
        }

        // If client-side validation passes, check with server
        fetch('/accounts/check-username/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ username: username })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.available) {
                usernameStatus.textContent = '✓ Username is available';
                usernameStatus.className = 'username-status available';
                usernameInput.classList.remove('invalid');
                usernameInput.classList.add('valid');
            } else {
                usernameStatus.textContent = '✗ Username is already taken';
                usernameStatus.className = 'username-status unavailable';
                usernameInput.classList.remove('valid');
                usernameInput.classList.add('invalid');
            }
        })
        .catch(error => {
            usernameStatus.textContent = 'Error checking username availability';
            usernameStatus.className = 'username-status error';
            usernameInput.classList.remove('valid', 'invalid');
        });
    }

    usernameInput.addEventListener('input', function(e) {
        const username = e.target.value.trim();
        
        // Clear previous status
        usernameStatus.textContent = 'Checking...';
        usernameStatus.className = 'username-status checking';
        usernameInput.classList.remove('valid', 'invalid');
        
        // Clear previous timer
        clearTimeout(debounceTimer);
        
        if (!username) {
            usernameStatus.textContent = 'Username is required';
            usernameStatus.className = 'username-status error';
            usernameInput.classList.add('invalid');
            return;
        }
        
        // Set new timer with reduced delay for better responsiveness
        debounceTimer = setTimeout(() => {
            checkUsername(username);
        }, 300); // Reduced from 500ms to 300ms for better responsiveness
    });
});