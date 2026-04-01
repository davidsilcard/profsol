from .models import SiteContent


def site_content(request):
    return {
        "global_site_content": SiteContent.current(),
    }
