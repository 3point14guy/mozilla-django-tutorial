from django.shortcuts import render
from catalog.models import Book, Author, BookInstance, Genre
# Create your views here.
def index(request):
    """View function for homepage of site."""

    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()
    # 'all()' is implied below
    num_authors = Author.objects.count()
    num_genres = Genre.objects.count()
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_visits': num_visits,
    }

    return render(request, 'index.html', context=context)

from django.views import generic

class BookListView(generic.ListView):
    model = Book
    paginate_by = 2
    context_object_name = 'book_list'
    queryset = Book.objects.all()
    # queryset = Book.objects.filter(title__icontains='war')[:5]
    template_name = 'books/book_list.html'

    # we can override the get_queryset() method to change the list of records returned. This is more flexible than just setting the queryset attribute as we did in the preceding code fragment (though there is no real benefit in this case):

    # def get_queryset(self):
    #     return Book.objects.filter(title__icontains='war')[:5]

class BookDetailView(generic.DetailView):
    model = Book

class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 2
    context_object_name = 'author_list'
    queryset = Author.objects.all()
    template_name = 'authors/author_list.html'

class AuthorDetailView(generic.DetailView):
    model = Author
