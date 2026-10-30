from django.urls import path
from . import views

app_name = 'crawling'
urlpatterns = [
    path('comments/company/', views.index, name='index'),
    path('comments/company/stream/', views.crawl_stream, name='crawl_stream'),
]