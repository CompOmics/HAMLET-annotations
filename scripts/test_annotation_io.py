import unittest
from annotation_io import entries, representation


class AnnotationFormats(unittest.TestCase):
    def test_multivalue_is_not_collapsed(self):
        original = [{'value': 'human', 'evidence': 'human'}, {'value': 'mouse', 'evidence': 'mouse'}]
        self.assertIs(entries(original), original)
        self.assertEqual(representation(original), 'object_list')

    def test_legacy_pair_is_read_without_mutation(self):
        original = ['human', 'human samples']
        self.assertEqual(entries(original), [{'value': 'human', 'evidence': 'human samples'}])
        self.assertEqual(original, ['human', 'human samples'])
        self.assertEqual(representation(original), 'legacy_pair')

    def test_singleton_preserves_normalization_metadata(self):
        original = {'value': 'brain', 'evidence': 'brain', 'is_normalized': True,
                    'ontology_id': 'UBERON:0000955', 'normalization_qc_flags': ['review']}
        self.assertIs(entries(original)[0], original)
        self.assertEqual(representation(original), 'single_object')

    def test_unknown_retained(self):
        self.assertEqual(entries(['unknown', '']), [{'value': 'unknown', 'evidence': ''}])

    def test_unsupported_format_fails_loudly(self):
        for value in (None, 'human', [], ['a', 'b', 'c'], {'value': 'human'}):
            with self.assertRaises(ValueError):
                entries(value)


if __name__ == '__main__':
    unittest.main()
