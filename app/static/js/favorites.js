document.addEventListener('click', function (e) {
  const el = e.target.closest('.heart-icon');
  if (!el) return;
  e.stopPropagation();

  const itemId = el.dataset.itemId;
  const isFavorited = el.classList.contains('favorited');

  if (isFavorited) {
    // remove favorite (your existing remove route is GET)
    fetch(`/favorites/remove/${itemId}`)
      .then(resp => {
        if (!resp.ok) throw new Error('Network');
        el.classList.remove('bi-heart-fill', 'favorited');
        el.classList.add('bi-heart');
        el.title = 'Add to favorites';
      })
      .catch(() => alert('Could not remove favorite.'));
  } else {
    // add favorite (your existing add route accepts POST)
    fetch(`/favorites/add/${itemId}`, { method: 'POST' })
      .then(resp => {
        if (!resp.ok) throw new Error('Network');
        el.classList.remove('bi-heart');
        el.classList.add('bi-heart-fill', 'favorited');
        el.title = 'Remove from favorites';
      })
      .catch(() => alert('Could not add favorite.'));
  }
});