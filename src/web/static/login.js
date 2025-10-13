document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('errorMessage');
    const signinBtn = document.getElementById('signinBtn');
    const btnText = signinBtn.querySelector('.btn-text');
    const btnLoader = signinBtn.querySelector('.btn-loader');

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Clear any previous errors
        errorMessage.style.display = 'none';
        
        // Get form data
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Disable button and show loader
        signinBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Success - redirect to dashboard
                window.location.href = '/';
            } else {
                // Show error
                errorMessage.textContent = data.message || 'Invalid username or password';
                errorMessage.style.display = 'block';
                
                // Re-enable button
                signinBtn.disabled = false;
                btnText.style.display = 'inline';
                btnLoader.style.display = 'none';
            }
        } catch (error) {
            console.error('Login error:', error);
            errorMessage.textContent = 'An error occurred. Please try again.';
            errorMessage.style.display = 'block';
            
            // Re-enable button
            signinBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    });
    
    // Enter key submit
    document.getElementById('password').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loginForm.dispatchEvent(new Event('submit'));
        }
    });
});


