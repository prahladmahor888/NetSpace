// Search functionality
document.querySelector('input[type="text"]').addEventListener('keyup', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
        
        if (text.includes(searchTerm)) {
            row.classList.add('animate__fadeIn');
            setTimeout(() => row.classList.remove('animate__fadeIn'), 500);
        }
    });
});

// Add animation when adding/removing users
document.querySelectorAll('button').forEach(button => {
    button.addEventListener('click', function(e) {
        if (this.textContent === 'Delete') {
            const row = this.closest('tr');
            row.classList.add('animate__fadeOut');
            setTimeout(() => row.style.display = 'none', 500);
        }
    });
});

// Responsive table adjustments
const adjustTable = () => {
    const table = document.querySelector('table');
    if (window.innerWidth < 640) {
        table.classList.add('table-compact');
    } else {
        table.classList.remove('table-compact');
    }
};

window.addEventListener('resize', adjustTable);
adjustTable();

// Add smooth counter animation for stats
function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        element.textContent = Math.floor(current);
        
        if (current >= end) {
            clearInterval(timer);
            element.textContent = end;
        }
    }, 16);
}

// Initialize counter animations
document.querySelectorAll('.stats-card h3').forEach(counter => {
    const value = parseInt(counter.textContent);
    counter.textContent = '0';
    animateValue(counter, 0, value, 1000);
});

// Table sorting
document.querySelectorAll('th.group').forEach(header => {
    header.addEventListener('click', () => {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aText = a.querySelector(`td:nth-child(${header.cellIndex + 1})`).textContent;
            const bText = b.querySelector(`td:nth-child(${header.cellIndex + 1})`).textContent;
            return aText.localeCompare(bText);
        });
        
        rows.forEach(row => {
            row.style.opacity = '0';
            tbody.appendChild(row);
            requestAnimationFrame(() => row.style.opacity = '1');
        });
    });
});

// Filter functionality
document.querySelectorAll('select').forEach(select => {
    select.addEventListener('change', function() {
        const rows = document.querySelectorAll('tbody tr');
        const status = document.querySelector('select:first-child').value;
        const role = document.querySelector('select:last-child').value;
        
        rows.forEach(row => {
            const rowStatus = row.querySelector('td:nth-child(3)').textContent.trim();
            const rowRole = row.querySelector('td:nth-child(1)').textContent.trim();
            
            const statusMatch = status === 'All Status' || rowStatus === status;
            const roleMatch = role === 'All Roles' || rowRole.includes(role);
            
            if (statusMatch && roleMatch) {
                row.style.display = '';
                row.style.animation = 'fadeIn 0.5s ease-out';
            } else {
                row.style.display = 'none';
            }
        });
    });
});

// Remove user type tabs filtering code and update select filtering
document.querySelector('#roleFilter').addEventListener('change', function() {
    const rows = document.querySelectorAll('tbody tr');
    const selectedRole = this.value.toLowerCase();
    
    rows.forEach(row => {
        const isAdmin = row.dataset.userType === 'admin';
        const shouldShow = 
            selectedRole === 'all users' || 
            (selectedRole === 'administrators' && isAdmin) ||
            (selectedRole === 'regular users' && !isAdmin);
        
        if (shouldShow) {
            row.style.display = '';
            row.classList.remove('hidden');
            row.classList.add('animate__fadeIn');
        } else {
            row.classList.add('hidden');
            setTimeout(() => row.style.display = 'none', 300);
        }
    });
});

// Export functionality
document.querySelector('button:contains("Export")').addEventListener('click', () => {
    const table = document.querySelector('table');
    const rows = Array.from(table.querySelectorAll('tr'));
    
    const csvContent = rows
        .map(row => {
            return Array.from(row.querySelectorAll('td, th'))
                .map(cell => cell.textContent.trim())
                .join(',');
        })
        .join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', 'users_export.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
});

// Admin List Modal Toggle
function toggleAdminList() {
    const modal = document.getElementById('adminListModal');
    if (modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        setTimeout(() => {
            modal.querySelector('.transform').classList.add('scale-100');
            modal.querySelector('.transform').classList.remove('scale-95');
        }, 10);
    } else {
        modal.querySelector('.transform').classList.add('scale-95');
        modal.querySelector('.transform').classList.remove('scale-100');
        setTimeout(() => {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }, 300);
    }
}

// Close modal on outside click
document.getElementById('adminListModal').addEventListener('click', function(e) {
    if (e.target === this) {
        toggleAdminList();
    }
});
