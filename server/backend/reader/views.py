from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Avg  # Add this import
from .models import ChapterView 
from django.urls import reverse_lazy as reverse
from django.contrib.auth.forms import UserCreationForm
from .models import Comic, Category, Chapter, Comment, Rating, Bookmark, Product, Payment

class ComicListView(ListView):
    model = Comic
    template_name = 'reader/comic_list.html'
    context_object_name = 'comics'
    paginate_by = 12
    
    def get_queryset(self):
        return Comic.objects.filter(active=True)


class CategoryListView(ListView):
    model = Category
    template_name = 'reader/category_list.html'
    context_object_name = 'categories'
class CategoryDetailView(DetailView):
    model = Category
    template_name = 'reader/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()  # Fix: get_object() not get.object()
        context['comics'] = category.comics.filter(active=True)  # Fix: category.comics not self.comics
        return context


class BookmarkToggleView(LoginRequiredMixin, View):
    def post(self, request, slug):
        comic = get_object_or_404(Comic, slug=slug)
        bookmark, created = Bookmark.objects.get_or_create(comic=comic, creator=request.user)
        if not created:
            bookmark.delete()
            return JsonResponse({'status': 'removed'})
        return JsonResponse({'status': 'added'})
class RateComicView(LoginRequiredMixin, View):
    def post(self, request, slug):
        comic = get_object_or_404(Comic, slug=slug)
        rating_value = request.POST.get('rating')
        if rating_value:
            rating, created = Rating.objects.get_or_create(
                comic=comic, 
                creator=request.user,
                defaults={'rate': int(rating_value)}  # Fix: use 'rate' not 'rate_value'
            )
            if not created:
                rating.rate = int(rating_value)  # Fix: use 'rate' not 'value'
                rating.save()
            avg_rating = comic.rating_set.aggregate(Avg('rate'))['rate__avg']  # Fix: use 'rate'
            return JsonResponse({'status': 'rated', 'average_rating': avg_rating})
        return JsonResponse({'status': 'error', 'message': 'Invalid rating'})

class AddCommentView(LoginRequiredMixin, View):
    def post(self, request, slug):
        comic = get_object_or_404(Comic, slug=slug)
        content = request.POST.get('content')
        if content:
            comment = Comment.objects.create(content=content, comic=comic, creator=request.user)
            return JsonResponse({'status': 'comment_added', 'comment_id': comment.id})
        return JsonResponse({'status': 'error', 'message': 'Invalid comment'})
class ReplyCommentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        content = request.POST.get('content')
        if content:
            reply = Comment.objects.create(content=content, comic=comment.comic, creator=request.user, reply_to=comment)
            return JsonResponse({'status': 'reply_added', 'reply_id': reply.id})
        return JsonResponse({'status': 'error', 'message': 'Invalid reply'})
class ProfileView(LoginRequiredMixin, ListView):
    model = Bookmark
    template_name = 'reader/profile.html'
    context_object_name = 'bookmarks'

    def get_queryset(self):
        return self.model.objects.filter(creator=self.request.user)
class BookmarkListView(LoginRequiredMixin, ListView):
    model = Bookmark
    template_name = 'reader/bookmark_list.html'
    context_object_name = 'bookmarks'

    def get_queryset(self):
        return self.model.objects.filter(creator=self.request.user)
class ProductListView(ListView):
    model = Product
    template_name = 'reader/product_list.html'
    context_object_name = 'products'
class BuyCoinsView(LoginRequiredMixin, View):
    def get(self, request):
        products = Product.objects.filter(category=Product.TYPES.COIN, active=True)
        return render(request, 'reader/buy_coins.html', {'products': products})
class BuyChapterView(LoginRequiredMixin, View):
    def get(self, request, slug):
        comic = get_object_or_404(Comic, slug=slug)
        products = Product.objects.filter(category=Product.TYPES.CHAPTER, active=True)
        return render(request, 'reader/buy_chapter.html', {'comic': comic, 'products': products})
class PaymentSuccessView(View):
    def get(self, request):
        return render(request, 'reader/payment_success.html')
class PaymentCancelView(View):
    def get(self, request):
        return render(request, 'reader/payment_cancel.html')
class ComicSearchView(ListView):
    model = Comic
    template_name = 'comics/search_results.html'
    context_object_name = 'comics'
    paginate_by = 12


class LatestComicsView(ListView):
    model = Comic
    template_name = 'reader/latest_comics.html'
    context_object_name = 'comics'
    paginate_by = 12

    def get_queryset(self):
        return Comic.objects.filter(active=True).order_by('-created_date')  


class PopularComicsView(ListView):
    model = Comic
    template_name = 'reader/popular_comics.html'
    context_object_name = 'comics'
    paginate_by = 12

    def get_queryset(self):
        return Comic.objects.filter(active=True).annotate(
            avg_rating=Avg('rating_set__rate')  # Fix: use rating_set__rate
        ).order_by('-avg_rating')
class ChapterViewUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chapter = get_object_or_404(Chapter, pk=pk)
        chapter_view, created = ChapterView.objects.get_or_create(chapter=chapter)
        chapter_view.views += 1
        chapter_view.save()
        return JsonResponse({'status': 'viewed', 'views': chapter_view.views})

# Create your views here.
