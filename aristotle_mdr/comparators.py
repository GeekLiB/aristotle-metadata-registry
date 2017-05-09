from reversion_compare.mixins import CompareMixin, CompareMethodsMixin
from django.template.loader import render_to_string


class Comparator(CompareMixin, CompareMethodsMixin):
    pass


class ValueDomainComparator(Comparator):
    """
    Value Domains can be compared by their values as well as their text.
    A raw comparison of the value objects will fail though as they are
    specific to their value domain.

    Another approach is needed.
    """

    def compare_supplementaryvalue_set(self, obj_compare):
        return self.compare_value_set(obj_compare)

    def compare_permissiblevalue_set(self, obj_compare):
        return self.compare_value_set(obj_compare)

    def compare_value_set(self, obj_compare):
        change_info = obj_compare.get_m2o_change_info()

        same_meanings_added = []
        same_meanings_removed = []
        same_items_added = []
        same_items_removed = []
        removed_items = change_info['removed_items']
        added_items = change_info['added_items']
        for removed in removed_items:
            for added in added_items:

                if (
                    removed.object.meaning == added.object.meaning and
                    removed.object.value == added.object.value
                ):
                    same_items_added.append(added)
                    same_items_removed.append(removed)
                elif (removed.object.meaning == added.object.meaning):
                    if added not in same_meanings_added and removed not in same_meanings_removed:
                        same_meanings_added.append(added)
                        same_meanings_removed.append(removed)
        for same in same_meanings_removed + same_items_removed:
            if same in removed_items:
                removed_items.remove(same)
        for same in same_meanings_added + same_items_added:
            added_items.remove(same)

        change_info.update({
            'removed_items': removed_items,
            'added_items': added_items,
            'same_items': change_info['same_items'] + same_items_added,
            'same_values': zip(same_meanings_added, same_meanings_removed)
        })

        context = {"change_info": change_info}
        return render_to_string("aristotle_mdr/actions/compare/valuedomain_valueset.html", context)
