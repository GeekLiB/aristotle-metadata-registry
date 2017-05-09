from aristotle_mdr.utils import get_download_template_path_for_item
from django.shortcuts import render

item_register = {
    'txt': '__all__'
}

def download(request, download_type, item):

    template = get_download_template_path_for_item(item, download_type)

    response = render(request, template, {'item': item}, content_type='text/plain')

    return response
