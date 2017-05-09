"""
This file contains code required for the v1.3.x -> 1.4.x data migrations
At some point, we will squash the entire migration path for <1.4 and remove this before we have too many users
running this code.
"""
from django.db import migrations, models
import ckeditor_uploader.fields

from django.db.migrations.operations.base import Operation


class classproperty(object):

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class MoveConceptFields(Operation):

    reversible = False

    def __init__(self, model_name):
        self.model_name = model_name

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):

        if schema_editor.connection.vendor == 'sqlite':
            concept_table_name = "%s_%s" % (app_label, self.model_name)
            for column in [
                'comments', 'origin_URI', 'references', 'responsible_organisation',
                'short_name', 'submitting_organisation', 'superseded_by_id',
                'synonyms', 'version'
            ]:
                base_query = """
                    update aristotle_mdr__concept
                        set temp_col_%s = (
                            select "%s"."%s"
                            from %s
                            where %s._concept_ptr_id = aristotle_mdr__concept.id
                        )
                        where exists ( select * from %s where %s._concept_ptr_id = aristotle_mdr__concept.id)
                """ % tuple(
                    [column, concept_table_name, column, concept_table_name, concept_table_name, concept_table_name, concept_table_name]
                )
                schema_editor.execute(base_query)
        else:
            concept_table_name = "%s_%s" % (app_label, self.model_name)
            base_query = """
                UPDATE  "aristotle_mdr__concept"
                SET     "temp_col_comments" = "%s"."comments",
                        "temp_col_origin_URI" = "%s"."origin_URI",
                        "temp_col_references" = "%s"."references",
                        "temp_col_responsible_organisation" = "%s"."responsible_organisation",
                        "temp_col_short_name" = "%s"."short_name",
                        "temp_col_submitting_organisation" = "%s"."submitting_organisation",
                        "temp_col_superseded_by_id" = "%s"."superseded_by_id",
                        "temp_col_synonyms" = "%s"."synonyms",
                        "temp_col_version" = "%s"."version"
                FROM    %s
                WHERE   "aristotle_mdr__concept"."id" = "%s"."_concept_ptr_id"
                ;
            """ % tuple([concept_table_name] * 11)
            schema_editor.execute(base_query)

    def describe(self):
        return "Creates extension %s" % self.name


class ConceptMigrationAddConceptFields(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='_concept',
            name='temp_col_comments',
            field=ckeditor_uploader.fields.RichTextUploadingField(help_text='Descriptive comments about the metadata item.', blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_origin_URI',
            field=models.URLField(help_text='If imported, the original location of the item', blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_references',
            field=ckeditor_uploader.fields.RichTextUploadingField(blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_responsible_organisation',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_short_name',
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_submitting_organisation',
            field=models.CharField(max_length=256, blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_superseded_by',
            field=models.ForeignKey(related_name='supersedes', blank=True, to='aristotle_mdr._concept', null=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_synonyms',
            field=models.CharField(max_length=200, blank=True),
        ),
        migrations.AddField(
            model_name='_concept',
            name='temp_col_version',
            field=models.CharField(max_length=20, blank=True),
        ),
    ]


class ConceptMigration(migrations.Migration):

    @classproperty
    def operations(cls):
        copy_operations = []
        delete_operations = []

        for model in cls.models_to_fix:
            copy_operations.append(MoveConceptFields(model_name=model))
            delete_operations += [
                migrations.RemoveField(
                    model_name=model,
                    name='comments',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='origin_URI',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='references',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='responsible_organisation',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='short_name',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='submitting_organisation',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='superseded_by',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='synonyms',
                ),
                migrations.RemoveField(
                    model_name=model,
                    name='version',
                )
            ]
        return copy_operations + delete_operations


class ConceptMigrationRenameConceptFields(migrations.Migration):
    operations = [
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_comments',
            new_name='comments',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_origin_URI',
            new_name='origin_URI',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_references',
            new_name='references',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_responsible_organisation',
            new_name='responsible_organisation',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_short_name',
            new_name='short_name',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_submitting_organisation',
            new_name='submitting_organisation',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_superseded_by',
            new_name='superseded_by',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_synonyms',
            new_name='synonyms',
        ),
        migrations.RenameField(
            model_name='_concept',
            old_name='temp_col_version',
            new_name='version',
        ),
    ]
