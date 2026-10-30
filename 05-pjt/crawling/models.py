from django.db import models

# 데이터 수집, 전처리, 증강 각 단계의 결과를 저장하는 모델
class CommentTaskResult(models.Model):
    
    # 1. 실제 매칭된 종목의 공식 명칭
    actual_company_name = models.CharField(
        max_length=100, 
        verbose_name='실제종목명'
    )
    
    # 2. 원본 댓글 목록 (크롤링 직후의 데이터 리스트)
    original_comments = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name='원본 댓글 목록',
        help_text="리스트 형태로 원본 문자열들을 저장합니다."
    )
    
    # 3. 정제 댓글 목록 (전처리 파이프라인을 거친 데이터 리스트)
    cleaned_comments = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name='정제 댓글 목록'
    )
    
    # 4. 증강 댓글 목록 (최종적으로 증강된 데이터 리스트)
    augmented_comments = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name='증강 댓글 목록'
    )
    
    # 5. IQR 임계값 정보 (이상치 제거 등에 사용된 IQR 관련 수치들을 딕셔너리 형태로 저장)
    # 예: {"Q1": 10, "Q3": 50, "lower_bound": -50, "upper_bound": 110}
    iqr_thresholds = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='IQR 임계값 정보'
    )
    
    # 6. 생성 일시
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='생성 일시'
    )

    stock_snapshot = models.JSONField(default=dict, blank=True, verbose_name='수집 시점 주가')
    sentiment_analysis = models.JSONField(default=dict, blank=True, verbose_name='댓글 요약 및 감성분석')

    class Meta:
        db_table = 'comment_task_result'
        verbose_name = '댓글 증강 파이프라인 결과'
        verbose_name_plural = '댓글 증강 파이프라인 결과 목록'
        # 최신 데이터가 가장 먼저 조회되도록 정렬 기준 설정
        ordering = ['-created_at']

    def __str__(self):
        # Admin 페이지 등에서 객체를 출력할 때 보여질 문자열
        date_str = self.created_at.strftime('%Y-%m-%d %H:%M')
        return f"[{self.actual_company_name}] 증강 결과 ({date_str})"