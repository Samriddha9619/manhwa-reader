from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.conf import settings
from cloudinary.models import CloudinaryField


User = get_user_model()

# Custom base model (assumed structure)
class MyModelBase(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True

class Comic(MyModelBase):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    artist = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, choices=[
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('hiatus', 'Hiatus'),
    ], default='ongoing')
    
    # Cloudinary image fields
    cover_image = CloudinaryField('image', blank=True, null=True, folder='manhwa/covers/')
    thumbnail = CloudinaryField('image', blank=True, null=True, folder='manhwa/thumbnails/')
    
    # Categories relationship
    categories = models.ManyToManyField('Category', related_name='comics', blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Chapter(MyModelBase):
    class Meta:
        unique_together = ('chapter_num', 'comic')
        ordering = ["-id"]

    title = models.TextField(null=True, blank=True, default="None")
    chapter_num = models.PositiveIntegerField(null=False)
    slug = models.SlugField(blank=True, null=True)
    price = models.IntegerField(default=0)
    comic = models.ForeignKey(Comic, related_name="chapters", on_delete=models.CASCADE, null=True)

    def save(self, *args, **kwargs):
        # Auto increment if not set
        if not self.chapter_num:
            last_chapter = Chapter.objects.filter(comic=self.comic).order_by('chapter_num').last()
            self.chapter_num = 1 if not last_chapter else last_chapter.chapter_num + 1

        # Auto slug
        if not self.slug:
            self.slug = f"chapter-{self.chapter_num}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ch.{self.chapter_num} of {self.comic.title}"

    def get_previous_chapter(self):
        return Chapter.objects.filter(
            comic=self.comic,
            chapter_num__lt=self.chapter_num,
            active=True
        ).order_by('-chapter_num').first()

    def get_next_chapter(self):
        return Chapter.objects.filter(
            comic=self.comic,
            chapter_num__gt=self.chapter_num,
            active=True
        ).order_by('chapter_num').first()


class ChapterImage(models.Model):
    image = CloudinaryField('image', folder='manhwa/chapters/')
    page_number = models.PositiveIntegerField(default=1)
    chapter = models.ForeignKey(Chapter, related_name="chapter_images", on_delete=models.CASCADE, null=True)
    
    class Meta:
        ordering = ['page_number']
        unique_together = ('chapter', 'page_number')
    
    def __str__(self):
        return f"Page {self.page_number} of {self.chapter}"


class ChapterView(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    views = models.IntegerField(default=0)
    chapter = models.OneToOneField(Chapter, on_delete=models.CASCADE, null=True)

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Comment(models.Model):
    content = models.TextField()
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    reply_to = models.ForeignKey("self", null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.content


class Rating(models.Model):
    rate = models.PositiveSmallIntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)


class Bookmark(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)


class Product(models.Model):
    class TYPES(models.TextChoices):
        COIN = 'C', 'COIN'
        CHAPTER = 'CH', 'CHAPTER'

    stripe_product_id = models.CharField(max_length=50, null=True, editable=False)
    stripe_price_id = models.CharField(max_length=50, null=True, editable=False)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(
        max_length=2,
        choices=TYPES.choices,
        default=TYPES.COIN
    )

    def __str__(self):
        return f"{self.category} - {self.price}"
class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='pending')
    payment_id = models.CharField(max_length=100, unique=True)  # e.g., from Stripe
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status} - {self.amount}"

