from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, modify_settings
from django.test.utils import setup_test_environment

from aristotle_mdr.contrib.identifiers import models as ID
from aristotle_mdr import models as MDR
from aristotle_mdr.tests import utils
from aristotle_mdr.utils import url_slugify_concept

setup_test_environment()


class TestIdentifiers(utils.LoggedInViewPages, TestCase):
    def test_identifier_displays(self):
        jl = MDR.Organization.objects.create(
            name="Justice League of America",
            definition="Fighting for Truth Justice and Liberty"
        )
        ns_jla = ID.Namespace.objects.create(
            naming_authority=jl,
            shorthand_prefix='jla',
        )
        meta = MDR.ObjectClass.objects.create(
            name="Metahuman",
            definition=(
                "A human-like being with extranormal powers and abilities,"
                "be they technological, alien, mutant, or magical in nature."
            ),
            references="https://en.wikipedia.org/wiki/Metahuman"
        )
        meta_jl_id = ID.ScopedIdentifier.objects.create(
            concept=meta.concept, identifier="metahumans", namespace=ns_jla
        )
        self.assertEqual(
            str(meta_jl_id),
            "{0}:{1}:{2}".format(jl.name, meta_jl_id.identifier, meta_jl_id.version)
        )

    def test_identifier_redirects(self):
        jl = MDR.Organization.objects.create(
            name="Justice League of America",
            definition="Fighting for Truth Justice and Liberty"
        )
        sra = MDR.Organization.objects.create(
            name="Super-human Registration Authority",
            definition="Protecting humans from unregistered mutant activity"
        )
        ns_jla = ID.Namespace.objects.create(
            naming_authority=jl,
            shorthand_prefix='jla',
        )
        ns_sra = ID.Namespace.objects.create(
            naming_authority=sra,
            shorthand_prefix='sra',
        )
        meta = MDR.ObjectClass.objects.create(
            name="Metahuman",
            definition=(
                "A human-like being with extranormal powers and abilities,"
                "be they technological, alien, mutant, or magical in nature."
            ),
            references="https://en.wikipedia.org/wiki/Metahuman"
        )

        meta_jl_id = ID.ScopedIdentifier.objects.create(
            concept=meta.concept, identifier="metahumans", namespace=ns_jla
        )
        meta_sra_id = ID.ScopedIdentifier.objects.create(
            concept=meta.concept, identifier="mutants", namespace=ns_sra
        )

        self.login_superuser()

        response = self.client.get(
            reverse(
                'aristotle_identifiers:scoped_identifier_redirect',
                args=[
                    meta_jl_id.namespace.shorthand_prefix,
                    meta_jl_id.identifier
                ]
            )
        )
        self.assertRedirects(response, url_slugify_concept(meta))

        response = self.client.get(
            reverse(
                'aristotle_identifiers:scoped_identifier_redirect',
                args=[
                    meta_sra_id.namespace.shorthand_prefix,
                    meta_sra_id.identifier
                ]
            )
        )
        self.assertRedirects(response, url_slugify_concept(meta))

        response = self.client.get(
            reverse(
                'aristotle_identifiers:scoped_identifier_redirect',
                args=[
                    meta_sra_id.namespace.shorthand_prefix,
                    "obviously_fake_id"
                ]
            )
        )
        self.assertEqual(response.status_code, 404)

        meta_jl_id_2 = ID.ScopedIdentifier.objects.create(
            concept=meta.concept, identifier="metahuman", namespace=ns_jla, version="1"
        )
        response = self.client.get(
            reverse(
                'aristotle_identifiers:scoped_identifier_redirect',
                args=[
                    meta_jl_id_2.namespace.shorthand_prefix,
                    meta_jl_id_2.identifier
                ]
            ),
            {'v': 1}
        )
        self.assertRedirects(response, url_slugify_concept(meta))
