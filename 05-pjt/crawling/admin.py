from django.contrib import admin
from .models import CommentTaskResult

@admin.register(CommentTaskResult)
class CommentTaskResultAdmin(admin.ModelAdmin):
    # Admin 페이지 목록에서 보여줄 필드들
    list_display = ('actual_company_name', 'get_original_count', 'get_cleaned_count', 'get_augmented_count', 'created_at')
    
    # 검색 기능
    search_fields = ('actual_company_name',)
    
    # 필터 기능 (날짜별로 필터링)
    list_filter = ('created_at',)

    # 각 목록의 개수를 Admin 페이지에 표시하기 위한 커스텀 메서드
    def get_original_count(self, obj):
        return len(obj.original_comments) if obj.original_comments else 0
    get_original_count.short_description = '원본 댓글 수'

    def get_cleaned_count(self, obj):
        return len(obj.cleaned_comments) if obj.cleaned_comments else 0
    get_cleaned_count.short_description = '정제 댓글 수'

    def get_augmented_count(self, obj):
        return len(obj.augmented_comments) if obj.augmented_comments else 0
    get_augmented_count.short_description = '증강 댓글 수'