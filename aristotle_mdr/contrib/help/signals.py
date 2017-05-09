from django.db.models.signals import post_save, post_delete, pre_delete
# from reversion.signals import post_revision_commit
import haystack.signals as signals  # .RealtimeSignalProcessor as RealtimeSignalProcessor
from aristotle_mdr.signals import AristotleSignalProcessor


class AristotleHelpSignalProcessor(AristotleSignalProcessor):
    def setup(self):
        from aristotle_mdr.contrib.help.models import HelpPage, ConceptHelp
        post_save.connect(self.handle_save, sender=HelpPage)
        post_save.connect(self.handle_save, sender=ConceptHelp)
        super(AristotleHelpSignalProcessor, self).setup()
