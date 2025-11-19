// static/js/script.js
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Progress bar animation
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(() => {
            bar.style.transition = 'width 1s ease-in-out';
            bar.style.width = width;
        }, 100);
    });

    // Habit completion toggle
    document.querySelectorAll('.habit-complete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const habitId = this.dataset.habitId;
            // AJAX call to mark habit as complete
            fetch(`/habits/${habitId}/complete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.classList.toggle('completed');
                    this.innerHTML = this.classList.contains('completed') ? 
                        '<i class="fas fa-check"></i> Completed' : 
                        '<i class="fas fa-plus"></i> Mark Complete';
                }
            });
        });
    });

    // CSRF token function for AJAX
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Real-time notifications check
    function checkNotifications() {
        fetch('/api/notifications/unread-count/')
            .then(response => response.json())
            .then(data => {
                const badge = document.querySelector('.notification-count');
                if (badge && data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = 'flex';
                }
            });
    }

    // Check notifications every 30 seconds
    setInterval(checkNotifications, 30000);
});