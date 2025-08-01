from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg, Q
from .models import Comic, Category, Chapter, Comment, Rating, Bookmark, Product, Payment, ChapterView, User
from django.views.generic import ListView, DetailView, View
class ComicListView(ListView):
    model = Comic
    template_name = 'reader/comic_list.html'
    context_object_name = 'comics'
    paginate_by = 12
    
    def get_queryset(self):
        return Comic.objects.filter(active=True)
class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! Please login.')
        return super().form_valid(form)
class ComicDetailView(DetailView):
    model = Comic
    template_name = 'reader/comic_detail.html'
    context_object_name = 'comic'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comic = self.get_object()
        
        # Get chapters
        context['chapters'] = comic.chapters.filter(active=True).order_by('chapter_num')
        
        # Get comments (only top-level comments, replies are handled in template)
        context['comments'] = Comment.objects.filter(
            comic=comic, 
            reply_to=None
        ).order_by('-created_date')
        
        # Calculate average rating
        context['average_rating'] = Rating.objects.filter(comic=comic).aggregate(
            avg_rating=Avg('rate')
        )['avg_rating']
        
        # User-specific context if authenticated
        if self.request.user.is_authenticated:
            context['user_rating'] = Rating.objects.filter(
                comic=comic, 
                creator=self.request.user
            ).first()
            context['is_bookmarked'] = Bookmark.objects.filter(
                comic=comic, 
                creator=self.request.user
            ).exists()
        
        return context
    
class ChapterDetailView(DetailView):
    model = Chapter
    template_name = 'reader/chapter_detail.html'
    context_object_name = 'chapter'
    slug_field = 'slug'
    slug_url_kwarg = 'chapter_slug'
    
    def get_object(self):
        comic_slug = self.kwargs['comic_slug']
        chapter_slug = self.kwargs['chapter_slug']
        return get_object_or_404(
            Chapter, 
            comic__slug=comic_slug, 
            slug=chapter_slug,
            active=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chapter = self.get_object()
        
        context['comic'] = chapter.comic
        context['chapter_images'] = chapter.chapter_images.all()
        
        # Check if user has access to this chapter
        context['user_has_access'] = self.check_user_access(chapter)
        
        # Update view count (wrap in try/except to prevent errors)
        try:
            chapter_view, created = ChapterView.objects.get_or_create(chapter=chapter)
            chapter_view.views += 1
            chapter_view.save()
        except Exception as e:
            # Log the error but don't break the page
            print(f"Error updating chapter view count: {e}")
        
        return context
    
    def check_user_access(self, chapter):
        """Check if user has access to this chapter"""
        if chapter.price == 0:
            return True
        
        if not self.request.user.is_authenticated:
            return False
        
        # Check if user has purchased this chapter
        return Payment.objects.filter(
            user=self.request.user,
            chapter=chapter,
            is_complete=True
        ).exists()


class BuyChapterView(LoginRequiredMixin, View):
    def get(self, request, chapter_id):
        chapter = get_object_or_404(Chapter, id=chapter_id)
        return render(request, 'reader/buy_chapter.html', {
            'chapter': chapter,
            'comic': chapter.comic
        })
    
    def post(self, request, chapter_id):
        chapter = get_object_or_404(Chapter, id=chapter_id)
        user = request.user
        
        # Check if user already has access
        if Payment.objects.filter(user=user, chapter=chapter, is_complete=True).exists():
            return JsonResponse({
                'success': False, 
                'message': 'You already have access to this chapter.'
            })
        
        # Check if user has enough coins
        if user.coins < chapter.price:
            return JsonResponse({
                'success': False,
                'message': f'Insufficient coins. You need {chapter.price} coins but only have {user.coins}.'
            })
        
        # Process purchase
        user.coins -= chapter.price
        user.save()
        
        # Create payment record
        Payment.objects.create(
            user=user,
            chapter=chapter,
            category=Product.TYPES.CHAPTER,
            amount=chapter.price,
            is_complete=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Chapter unlocked successfully!',
            'remaining_coins': user.coins
        })






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
        products = Product.objects.filter(
            category=Product.TYPES.COIN, 
            active=True
        ).order_by('price')
        return render(request, 'reader/buy_coins.html', {'products': products})
    
    def post(self, request):
        # This is for the demo purchase - remove in production
        import json
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id, active=True)
            # Demo: Add 100 coins for any purchase
            request.user.coins += 100
            request.user.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Added 100 coins to your account!',
                'new_balance': request.user.coins
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Product not found'
            })

# Add a demo purchase URL (remove in production)
# Add this to your urls.py
path('demo-add-coins/', views.BuyCoinsView.as_view(), name='demo_add_coins'),


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

class SignUpView(CreateView):
    form_class = CustomUserCreationForm  # Use custom form instead
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! Please login.')
        return super().form_valid(form)
