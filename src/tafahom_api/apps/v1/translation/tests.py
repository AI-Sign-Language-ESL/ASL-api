from django.test import TestCase
from tafahom_api.apps.v1.translation.services.animation_service import translate_to_animation_names

class AnimationServiceTestCase(TestCase):
    def test_full_sentence_match(self):
        # "انا اسمي" should match as a full sentence.
        result = translate_to_animation_names("انا اسمي")
        self.assertEqual(result["animations"], ["ana_esmy"])
        self.assertEqual(result["unknown_words"], [])

    def test_greedy_phrase_matching(self):
        # "انا اسمي محمد" should match "انا اسمي" -> "ana_esmy", and "محمد" is unknown.
        result = translate_to_animation_names("انا اسمي محمد")
        self.assertEqual(result["animations"], ["ana_esmy"])
        self.assertEqual(result["unknown_words"], ["محمد"])

    def test_single_word_matches(self):
        # "ابن العم" -> "ebn_el3m" (phrase match), "ام" -> "om" (word match)
        # Input: "ابن العم ام"
        result = translate_to_animation_names("ابن العم ام")
        self.assertEqual(result["animations"], ["ebn_el3m", "om"])
        self.assertEqual(result["unknown_words"], [])

    def test_multiple_unknown_words(self):
        # Input: "مرحبا محمد" (both unknown)
        result = translate_to_animation_names("مرحبا محمد")
        self.assertEqual(result["animations"], [])
        self.assertEqual(result["unknown_words"], ["مرحبا", "محمد"])

    def test_whitespace_tolerance(self):
        # Input: "  انا   اسمي   "
        result = translate_to_animation_names("  انا   اسمي   ")
        self.assertEqual(result["animations"], ["ana_esmy"])
        self.assertEqual(result["unknown_words"], [])
