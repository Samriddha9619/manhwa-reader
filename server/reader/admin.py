from django.contrib import admin
from .models import Comic, Chapter, ChapterImage, Comment, Rating, Bookmark, Product, Category

# Inline admin for ChapterImage
class ChapterImageInline(admin.TabularInline):
    model = ChapterImage
    extra = 1
    fields = ('image', 'page_number')
    ordering = ['page_number']

# Chapter Admin with inline images
@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter_num', 'comic', 'price', 'active', 'created_at')
    list_filter = ('active', 'comic', 'created_at')
    search_fields = ('title', 'comic__title')
    inlines = [ChapterImageInline]
    readonly_fields = ('slug',)

# Comic Admin
@admin.register(Comic)
class ComicAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'active', 'created_at')
    list_filter = ('status', 'active', 'categories', 'created_at')
    search_fields = ('title', 'author', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'author', 'artist', 'status', 'active')
        }),
        ('Images', {
            'fields': ('cover_image', 'thumbnail')
        }),
        ('Categories', {
            'fields': ('categories',)
        }),
    )

# Register other models
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'comic', 'creator', 'created_date')
    list_filter = ('created_date', 'comic')
    search_fields = ('content', 'creator__username', 'comic__title')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('comic', 'creator', 'rate', 'created_date')
    list_filter = ('rate', 'created_date')
    search_fields = ('comic__title', 'creator__username')

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('comic', 'creator', 'created_date')
    list_filter = ('created_date',)
    search_fields = ('comic__title', 'creator__username')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'active', 'created_at')
    list_filter = ('category', 'active', 'created_at')
    search_fields = ('name',)
