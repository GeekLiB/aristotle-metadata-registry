from django.views.generic import TemplateView


class DynamicTemplateView(TemplateView):
    def get_template_names(self):
        return ['extension_test/static/%s.html' % self.kwargs['template']]
