import datetime
import uuid

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User, Permission

from catalog.models import Author, Book, BookInstance, Genre, Language

class AuthorListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        number_of_authors = 13

        for author_id in range(number_of_authors):
            Author.objects.create(
                first_name = f'Nicholas {author_id}',
                last_name = f'Nicolby {author_id}',
            )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/catalog/authors/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/author_list.html')

    def test_pagination_is_ten(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'] == True)
        self.assertTrue(len(response.context['author_list']) == 10)

    def test_lists_all_authors(self):
        response = self.client.get(reverse('authors')+'?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'] == True)
        self.assertTrue(len(response.context['author_list']) == 3)

class LoanedBooksByUserListViewTest(TestCase):
    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password="p@55w0rd")
        test_user2 = User.objects.create_user(username='testuser2', password="p@55w0rd")
        test_user1.save()
        test_user2.save()

        test_author = Author.objects.create(first_name="Joe", last_name="Mama")
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(name='English')
        test_book = Book.objects.create(
            title='Book Title',
            summary="a little blurb",
            isbn="123456789",
            author=test_author,
            language=test_language,
        )

        # create genre as a post-step
        genre_objects_for_book = Genre.objects.all()
        # direct assignment of many-to-many not allowed
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        number_of_book_copies = 30
        for book_copy in range(number_of_book_copies):
            return_date = timezone.now() + datetime.timedelta(days=book_copy%5)
            the_borrower = test_user1 if book_copy % 2 else test_user2
            status = 'm'
            BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 2016',
                due_back = return_date,
                borrower=the_borrower,
                status=status,
            )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(response, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_users_correct_template(self):
        login = self.client.login(username='testuser1', password="p@55w0rd")
        response = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        login = self.client.login(username='testuser1', password="p@55w0rd")
        response = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)

        # check that there are no books in the list initially (none on loan)
        self.assertTrue('bookinstance_list' in response.context)
        self.assertEqual(len(response.context['bookinstance_list']), 0)

        books = BookInstance.objects.all()[:10]

        for book in books:
            book.status = 'o'
            book.save()
        # repeating tests after putting books on loan
        response = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('bookinstance_list' in response.context)

        # confirm all books belong to testuser1 and are on loan
        for bookitem in response.context['bookinstance_list']:
            self.assertEqual(response.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):
        login = self.client.login(username='testuser1', password="p@55w0rd")

        for book in BookInstance.objects.all():
            book.status = 'o'
            book.save()

        response = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)

        self.assertTrue('bookinstance_list' in response.context)
        self.assertEqual(len(response.context['bookinstance_list']), 10)

        last_date = 0
        for book in response.context['bookinstance_list']:
            if last_date == 0:
                last_date = book.due_back
            else:
                self.assertTrue(last_date <= book.due_back)
                last_date = book.due_back

class RenewBookInstancesViewTest(TestCase):
    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password='p@55w0rd')
        test_user2 = User.objects.create_user(username='testuser2', password='p@55w0rd')

        test_user1.save()
        test_user2.save()

        # permission = Permission.objects.get(name="Set book as returned")
        # test_user2.user_permissions.add(permission)
        # test_user2.save()
        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

        test_author = Author.objects.create(first_name="Joe", last_name="Mama")
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(name='English')
        test_book = Book.objects.create(
            title='Book Title',
            summary="a little blurb",
            isbn="123456789",
            author=test_author,
            language=test_language,
        )

        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        # create a book instance for test_user1
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 2016',
                due_back = return_date,
                borrower=test_user1,
                status='o'
        )

        # create a book instance for test_user2
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance2 = BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 2016',
                due_back = return_date,
                borrower=test_user2,
                status='o'
        )

    def test_1_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        # manually check redirect. Can't use assertRedirect bc url will vary
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_2_redirect_if_logged_in_but_not_correct_permissions(self):
        login = self.client.login(username='testuser1', password='p@55w0rd')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 403)

    def test_3_logged_in_with_permission_borrowed_book(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance2.pk}))
        self.assertEqual(response.status_code, 200)

    def test_4_logged_in_with_permission_another_users_borrowed_book(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_5_HTTP404_for_invalid_book_if_logged_in(self):
        test_uid = uuid.uuid4()
        login = self.client.login(username='testuser2', password='p@55w0rd')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': test_uid}))
        self.assertEqual(response.status_code, 404)

    def test_6_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/book_renew_librarian.html')

    def test_7_form_renewal_date_is_initially_3_weeks_in_the_future(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 200)

        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(response.context['form'].initial['renewal_date'], date_3_weeks_in_future)

    def test_8_redirects_to_all_borrowed_book_list_on_success(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        valid_date_in_future = datetime.date.today() + datetime.timedelta(days=7)
        response = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk,}), {'renewal_date': valid_date_in_future})
        self.assertRedirects(response, reverse('all-borrowed'))

    def test_9_form_invalid_renewal_date_past(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        date_in_past = datetime.date.today() - datetime.timedelta(days=2)
        response = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}), {'renewal_date': date_in_past})
        self.assertEquals(response.status_code, 200)
        self.assertFormError(response, 'form', 'renewal_date', 'Invalid date - date selected is in the past.')

    def test_10_form_invalid_renewal_date_future(self):
        login = self.client.login(username='testuser2', password='p@55w0rd')
        invalid_future_date = datetime.date.today() + datetime.timedelta(weeks=5)
        response = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}), {'renewal_date': invalid_future_date})
        self.assertEquals(response.status_code, 200)
        self.assertFormError(response, 'form', 'renewal_date', 'Invalid date - date selected is more than 4 weeks from now.')
