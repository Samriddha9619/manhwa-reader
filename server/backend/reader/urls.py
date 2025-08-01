from django.urls import path
from . import views

app_name = 'reader'

urlpatterns = [
    path('', views.ComicListView.as_view(), name='comic_list'),
    path('comics/', views.ComicListView.as_view(), name='comics'),
    
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('category/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    
    path('comic/<slug:slug>/', views.ComicDetailView.as_view(), name='comic_detail'),
    path('comic/<slug:comic_slug>/chapter/<slug:chapter_slug>/', 
         views.ChapterDetailView.as_view(), name='chapter_detail'),
    
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('bookmarks/', views.BookmarkListView.as_view(), name='bookmarks'),
    
    path('comic/<slug:slug>/bookmark/', views.BookmarkToggleView.as_view(), name='bookmark_toggle'),
    path('comic/<slug:slug>/rate/', views.RateComicView.as_view(), name='rate_comic'),
    path('comic/<slug:slug>/comment/', views.AddCommentView.as_view(), name='add_comment'),
    path('comment/<int:pk>/reply/', views.ReplyCommentView.as_view(), name='reply_comment'),
    
    path('products/', views.ProductListView.as_view(), name='products'),
    path('buy-coins/', views.BuyCoinsView.as_view(), name='buy_coins'),
    path('buy-chapter/<int:chapter_id>/', views.BuyChapterView.as_view(), name='buy_chapter'),
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('payment/cancel/', views.PaymentCancelView.as_view(), name='payment_cancel'),
    
    
    path('search/', views.ComicSearchView.as_view(), name='comic_search'),
    path('latest/', views.LatestComicsView.as_view(), name='latest_comics'),
    path('popular/', views.PopularComicsView.as_view(), name='popular_comics'),
    
   
    path('api/chapter/<int:pk>/view/', views.ChapterViewUpdateView.as_view(), name='chapter_view_update'),
]
