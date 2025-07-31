from django.contrib import admin

# Register your models here.
from models import Comic, Chapter, Category, Comment, Rating, Bookmark, Product, Payment
admin.site.register(Comic)
admin.site.register(Chapter)
admin.site.register(Category)
admin.site.register(Comment)
admin.site.register(Rating)
admin.site.register(Bookmark)
admin.site.register(Product)
admin.site.register(Payment)