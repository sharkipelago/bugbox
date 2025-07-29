document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const issueList = document.getElementById('issue-list');
    const listItems = issueList.getElementsByTagName('a'); // Or other elements to search within
    const magnifyIcon = document.getElementById('magnify-icon')

    searchInput.addEventListener('input', function() {
        const searchTerm = searchInput.value.toLowerCase(); // Get input and convert to lowercase for case-insensitive search
        let lastItem = listItems[0];

        if (searchTerm.trim().length < 1) {
            [...listItems].forEach((_, index) => {
                listItems[index].style.display = 'none';
            });
            return;
        }

        let shownIssues = 0;
        for (let i = 0; i < listItems.length; i++) {
            const itemText = listItems[i].textContent.toLowerCase();
            if (itemText.includes(searchTerm)) {
                shownIssues++;
                listItems[i].style.display = 'block'; // Show the item
                lastItem.style.borderRadius = '0px 0px 0px 0px';
                listItems[i].style.borderRadius = '0px 0px 6px 6px';
                lastItem = listItems[i];
            } else {
                listItems[i].style.display = 'none'; // Hide the item
            }
        }

        console.log(shownIssues);
        if (shownIssues > 0) {
            searchInput.style.borderBottomLeftRadius  = '0px';
            magnifyIcon.style.borderBottomRightRadius  = '0px';
        }
        else {
            searchInput.style.borderBottomLeftRadius  = '6px';
            magnifyIcon.style.borderBottomRightRadius  = '6px';            
        }

    });
});