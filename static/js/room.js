document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const toggleParticipants = document.getElementById('toggleParticipants');
    const toggleChat = document.getElementById('toggleChat');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Toggle sidebar on mobile
    toggleParticipants.addEventListener('click', () => {
        sidebar.classList.toggle('show');
        activateTab('participants');
    });

    toggleChat.addEventListener('click', () => {
        sidebar.classList.toggle('show');
        activateTab('chat');
    });

    // Tab switching
    function activateTab(tabName) {
        tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });
    }

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => activateTab(btn.dataset.tab));
    });
});
