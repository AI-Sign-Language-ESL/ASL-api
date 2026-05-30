import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
import requests

class HybridTranslationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/translation/translate/'
        # Clear cache before each test
        cache.clear()

    @patch('tafahom_api.apps.v1.translation.services.ai_service.settings.AI_TEXT_TO_GLOSS_BASE_URL', 'http://mock-ai/translate')
    @patch('tafahom_api.apps.v1.translation.services.ai_service.requests.post')
    def test_successful_ai_translation(self, mock_post):
        # Mock successful AI response
        mock_response = mock_post.return_value
        mock_response.json.return_value = {"animations": ["hello", "world"]}
        mock_response.elapsed.total_seconds.return_value = 1.0
        
        payload = {"text": "مرحبا بك"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'ai')
        self.assertEqual(data['animations'], ["hello", "world"])
        
    @patch('tafahom_api.apps.v1.translation.services.ai_service.settings.AI_TEXT_TO_GLOSS_BASE_URL', 'http://mock-ai/translate')
    @patch('tafahom_api.apps.v1.translation.services.ai_service.requests.post')
    def test_ai_timeout_fallback_to_sign_matcher(self, mock_post):
        # Mock Timeout exception
        mock_post.side_effect = requests.exceptions.Timeout("AI Timed out")
        
        payload = {"text": "كيف حالك"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'sign_matcher')
        # "كيف حالك" maps to "kef_halak" in our SYNONYM_MAP
        self.assertEqual(data['animations'], ["kef_halak"])
        
    @patch('tafahom_api.apps.v1.translation.services.ai_service.settings.AI_TEXT_TO_GLOSS_BASE_URL', 'http://mock-ai/translate')
    @patch('tafahom_api.apps.v1.translation.services.ai_service.requests.post')
    def test_ai_exception_fallback(self, mock_post):
        # Mock Server Error exception
        mock_post.side_effect = requests.exceptions.RequestException("AI Server Error")
        
        payload = {"text": "نسيبي"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['source'], 'sign_matcher')
        self.assertEqual(data['animations'], ["nseby"])
        
    @patch('tafahom_api.apps.v1.translation.services.ai_service.settings.AI_TEXT_TO_GLOSS_BASE_URL', 'http://mock-ai/translate')
    @patch('tafahom_api.apps.v1.translation.services.ai_service.requests.post')
    def test_cache_hit_and_miss(self, mock_post):
        # Setup AI to return "ai_result"
        mock_response = mock_post.return_value
        mock_response.json.return_value = {"animations": ["test_anim"]}
        mock_response.elapsed.total_seconds.return_value = 0.5
        
        payload = {"text": "اختبار الكاش"}
        
        # Request 1: Cache Miss, hits AI
        response1 = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()['source'], 'ai')
        self.assertEqual(mock_post.call_count, 1)
        
        # Request 2: Cache Hit, doesn't hit AI
        response2 = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['source'], 'cache')
        self.assertEqual(response2.json()['animations'], ["test_anim"])
        # Call count should still be 1
        self.assertEqual(mock_post.call_count, 1)

    def test_empty_input(self):
        payload = {"text": "   "}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Text is required')
        
    def test_invalid_request_body(self):
        # Missing 'text' key
        payload = {"wrong_key": "مرحبا"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Text is required')
