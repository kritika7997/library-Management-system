const bookForm = document.querySelector('#book-form');
const bookList = document.querySelector('#book-list');
const bookCount = document.querySelector('#book-count');
const searchInput = document.querySelector('#book-search');
const formMessage = document.querySelector('#form-message');

let books = [];

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.detail || 'Something went wrong. Please try again.');
  }
  return response.json();
}

function renderBooks() {
  const query = searchInput.value.trim().toLowerCase();
  const visibleBooks = books.filter((book) =>
    `${book.title} ${book.author} ${book.isbn}`.toLowerCase().includes(query),
  );

  bookCount.textContent = `${books.length} ${books.length === 1 ? 'book' : 'books'} in your collection`;
  bookList.replaceChildren();

  if (visibleBooks.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = query ? 'No books match that search.' : 'Your shelf is empty. Add a book to get started.';
    bookList.append(empty);
    return;
  }

  visibleBooks.forEach((book) => {
    const row = document.createElement('article');
    row.className = 'book-row';

    const details = document.createElement('div');
    const title = document.createElement('h3');
    title.className = 'book-title';
    title.textContent = book.title;
    details.append(title);

    const metadata = [book.author, book.isbn ? `ISBN ${book.isbn}` : ''].filter(Boolean);
    if (metadata.length) {
      const meta = document.createElement('div');
      meta.className = 'book-meta';
      metadata.forEach((value) => {
        const item = document.createElement('span');
        item.textContent = value;
        meta.append(item);
      });
      details.append(meta);
    }

    const availability = document.createElement('button');
    availability.type = 'button';
    availability.className = `availability-button${book.is_available ? '' : ' checked-out'}`;
    availability.textContent = book.is_available ? 'Available' : 'Checked out';
    availability.setAttribute('aria-label', `${book.title}: ${book.is_available ? 'check out' : 'mark available'}`);
    availability.addEventListener('click', () => toggleAvailability(book));

    row.append(details, availability);
    bookList.append(row);
  });
}

async function loadBooks() {
  try {
    books = await request('/api/books');
    renderBooks();
  } catch (error) {
    bookCount.textContent = 'Could not load collection';
    bookList.replaceChildren();
    const message = document.createElement('p');
    message.className = 'empty-state';
    message.textContent = error.message;
    bookList.append(message);
  }
}

async function toggleAvailability(book) {
  try {
    const updatedBook = await request(`/api/books/${book.id}/availability`, {
      method: 'PATCH',
      body: JSON.stringify({ is_available: !book.is_available }),
    });
    books = books.map((item) => item.id === updatedBook.id ? updatedBook : item);
    renderBooks();
  } catch (error) {
    formMessage.textContent = error.message;
  }
}

bookForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  formMessage.textContent = '';
  const formData = new FormData(bookForm);
  const book = Object.fromEntries(formData.entries());
  book.title = book.title.trim();

  try {
    const createdBook = await request('/api/books', {
      method: 'POST',
      body: JSON.stringify(book),
    });
    books.push(createdBook);
    books.sort((first, second) => first.title.localeCompare(second.title));
    bookForm.reset();
    renderBooks();
    document.querySelector('#title').focus();
  } catch (error) {
    formMessage.textContent = error.message;
  }
});

searchInput.addEventListener('input', renderBooks);
loadBooks();
