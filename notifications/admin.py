from django.contrib import admin
from notifications.models import Tag, Post, DeletedPost


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug', 'created_at', 'updated_at')
    search_fields = ('title', 'slug', 'content')
    prepopulated_fields = {}  # Let our pre_save signal handle slug generation!
    filter_horizontal = ('tags',)


@admin.register(DeletedPost)
class DeletedPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_post_id', 'title', 'slug', 'deleted_at')
    search_fields = ('title', 'slug', 'content')
    readonly_fields = ('original_post_id', 'title', 'slug', 'content', 'deleted_at')
