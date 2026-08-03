content = """from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tickets.urls')),
]
"""

with open('ict_management/urls.py', 'w') as f:
    f.write(content)

print('Done!')