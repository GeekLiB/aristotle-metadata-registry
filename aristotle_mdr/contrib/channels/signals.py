from django.db.models.signals import post_save, post_delete, pre_delete, m2m_changed
# from reversion.signals import post_revision_commit
import haystack.signals as signals  # .RealtimeSignalProcessor as RealtimeSignalProcessor
from haystack_channels.signals import ChannelsRealTimeAsyncSignalProcessor
# Don't import aristotle_mdr.models directly, only pull in whats required,
#  otherwise Haystack gets into a circular dependancy.

# class AristotleSignalProcessor(signals.BaseSignalProcessor):
# Replace below with this when doing a dataload (shuts off Haystack)
#    pass


class AristotleChannelsSignalProcessor(ChannelsRealTimeAsyncSignalProcessor):
    def setup(self):
        super(AristotleChannelsSignalProcessor, self).setup()

        from aristotle_mdr.models import ReviewRequest, concept_visibility_updated

        post_save.connect(self.update_visibility_review_request, sender=ReviewRequest)
        m2m_changed.connect(self.update_visibility_review_request, sender=ReviewRequest.concepts.through)
        concept_visibility_updated.connect(self.handle_concept_recache)

    def teardown(self):  # pragma: no cover
        from aristotle_mdr.models import _concept
        post_save.disconnect(self.handle_concept_save, sender=_concept)
        # post_revision_commit.disconnect(self.handle_concept_revision)
        pre_delete.disconnect(self.handle_concept_delete, sender=_concept)
        super(AristotleSignalProcessor, self).teardown()

    def handle_concept_recache(self, concept, **kwargs):
        from aristotle_mdr.models import _concept
        instance = concept.item
        self.handle_save(instance.__class__, instance)

    def update_visibility_review_request(self, sender, instance, **kwargs):
        from aristotle_mdr.models import ReviewRequest
        assert(sender in [ReviewRequest, ReviewRequest.concepts.through])
        for concept in instance.concepts.all():
            obj = concept.item
            self.handle_save(obj.__class__, obj, **kwargs)
