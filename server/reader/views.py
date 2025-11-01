from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from  .forms import CustomUserCreationForm
from django.views.generic import CreateView
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg, Q
from .models import Comic, Chapter, Comment, Rating, Bookmark, Product, ChapterView, Category,Payment
from django.views.generic import ListView, DetailView, View
from pdf2image import convert_from_path
import tempfile
import os
from django.core.files.base import ContentFile
from io import BytesIO

class ComicListView(ListView):
    model = Comic
    template_name = 'reader/comic_list.html'
    context_object_name = 'comics'
    paginate_by = 12
    
    def get_queryset(self):
        return Comic.objects.filter(active=True)

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! Please login.')
        return super().form_valid(form)

class ComicDetailView(DetailView):
    model = Comic
    ordering = ['-created_at']
    template_name = 'reader/comic_detail.html'
    context_object_name = 'comic'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comic = self.get_object()
        
        context['chapters'] = comic.chapters.filter(active=True).order_by('chapter_num')
        
        context['comments'] = Comment.objects.filter(
            comic=comic, 
            reply_to=None
        ).order_by('-created_date')
        
        context['average_rating'] = Rating.objects.filter(comic=comic).aggregate(
            avg_rating=Avg('rate')
        )['avg_rating']
        
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
        
        images_count = chapter.chapter_images.count()
        print(f"DEBUG: Chapter {chapter.chapter_num} has {images_count} images")
        
        for img in chapter.chapter_images.all():
            print(f"  - Page {img.page_number}: {img.image.url}")
        
        context['comic'] = chapter.comic
        context['chapter_images'] = chapter.chapter_images.all()
        
        context['user_has_access'] = self.check_user_access(chapter)
        
        try:
            chapter_view, created = ChapterView.objects.get_or_create(chapter=chapter)
            chapter_view.views += 1
            chapter_view.save()
        except Exception as e:
            print(f"Error updating chapter view count: {e}")
        
        return context
    
    def check_user_access(self, chapter):
        if chapter.price == 0:
            return True
        
        if not self.request.user.is_authenticated:
            return False
        
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
        
        if Payment.objects.filter(user=user, chapter=chapter, is_complete=True).exists():
            return JsonResponse({
                'success': False, 
                'message': 'You already have access to this chapter.'
            })
        
        if user.coins < chapter.price:
            return JsonResponse({
                'success': False,
                'message': f'Insufficient coins. You need {chapter.price} coins but only have {user.coins}.'
            })
        
        user.coins -= chapter.price
        user.save()
        
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
        category = self.get_object()
        context['comics'] = Comic.objects.filter(categories=category, active=True)
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
                defaults={'rate': int(rating_value)}
            )
            if not created:
                rating.rate = int(rating_value)
                rating.save()
            avg_rating = comic.rating_set.aggregate(Avg('rate'))['rate__avg']
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
        import json
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id, active=True)
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
        return Comic.objects.filter(active=True).order_by('-created_at')

class PopularComicsView(ListView):
    model = Comic
    template_name = 'reader/popular_comics.html'
    context_object_name = 'comics'
    paginate_by = 12

    def get_queryset(self):
        return Comic.objects.filter(active=True).annotate(
            avg_rating=Avg('rating__rate')
        ).order_by('-avg_rating')

class ChapterViewUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        chapter = get_object_or_404(Chapter, pk=pk)
        chapter_view, created = ChapterView.objects.get_or_create(chapter=chapter)
        chapter_view.views += 1
        chapter_view.save()
        return JsonResponse({'status': 'viewed', 'views': chapter_view.views})

class UploadChapterImagesView(LoginRequiredMixin, View):
    def get(self, request, comic_slug):
        comic = get_object_or_404(Comic, slug=comic_slug)
        return render(request, 'reader/upload_chapter_images.html', {'comic': comic})
    
    def post(self, request, comic_slug):
        from reader.models import ChapterImage
        
        comic = get_object_or_404(Comic, slug=comic_slug)
        
        chapter_num = request.POST.get('chapter_num')
        chapter_title = request.POST.get('chapter_title', '')
        images = request.FILES.getlist('images')
        
        if not images:
            messages.error(request, 'Please upload at least one image')
            return redirect('reader:upload_chapter_images', comic_slug=comic_slug)
        
        chapter, created = Chapter.objects.get_or_create(
            comic=comic,
            chapter_num=chapter_num,
            defaults={'title': chapter_title}
        )
        
        if not created:
            chapter.chapter_images.all().delete()
        
        for page_num, image_file in enumerate(images, start=1):
            ChapterImage.objects.create(
                chapter=chapter,
                page_number=page_num,
                image=image_file
            )
        
        messages.success(request, f'Successfully uploaded {len(images)} pages!')
        return redirect('reader:chapter_detail', comic_slug=comic.slug, chapter_slug=chapter.slug)