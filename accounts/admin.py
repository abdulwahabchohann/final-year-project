from django.contrib import admin

from .models import Author, Book, Category, Genre


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'slug', 'source', 'created_at')
    search_fields = ('display_name', 'slug')
    list_filter = ('source',)
    ordering = ('display_name',)
    readonly_fields = ('created_at',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'website', 'created_at')
    search_fields = ('full_name',)
    ordering = ('full_name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'primary_author', 'published_year', 'average_rating', 'price')
    search_fields = (
        'title',
        'subtitle',
        'description',
        'isbn_10',
        'isbn_13',
        'authors__full_name',
    )
    list_filter = ('genres', 'language')
    filter_horizontal = ('authors', 'genres')
    readonly_fields = ('created_at', 'updated_at')
