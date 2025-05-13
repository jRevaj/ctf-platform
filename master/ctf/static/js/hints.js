function getHint(challengeUuid) {
    // Disable the button to prevent multiple clicks
    const hintButton = document.getElementById(`get-hint-btn-${challengeUuid}`);
    if (hintButton) {
        hintButton.disabled = true;
        hintButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
    }
    
    fetch(`challenges/${challengeUuid}/hint/`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).then(response => {
        if (!response.ok) {
            throw new Error(response.statusText);
        }
        return response.json();
    }).then(data => {
        if (data.new_hint) {
            const hintsHtml = document.getElementById(`hint-list-${challengeUuid}`);                
            const noHintsMessage = document.getElementById('no-hints-message');
            if (noHintsMessage) {
                noHintsMessage.remove();
            }
            
            const newHintHtml = `<li class="list-group-item py-2 px-3 border-1 border-tertiary text-muted rounded mb-1">
                <div class="d-flex justify-content-between align-items-center">
                    <p class="mb-0">${data.new_hint.hint}</p>
                    <span class="badge bg-danger ms-2">-${data.new_hint.points} pts</span>
                </div>
            </li>`;

            hintsHtml.insertAdjacentHTML('beforeend', newHintHtml);
            
            // Hide the button if no more hints are available
            if (!data.has_next_hint && hintButton) {
                hintButton.style.display = 'none';
            }
            
            // Show a toast notification
            showToast('Hint revealed! Check the hint section.', 'success');
        }
    }).catch(error => {
        console.error('Error getting hint:', error);
        showToast('Failed to get hint. Please try again.', 'danger');
    }).finally(() => {
        // Re-enable the button if it still exists
        if (hintButton) {
            hintButton.disabled = false;
            hintButton.innerHTML = 'Get a hint';
        }
    });
}