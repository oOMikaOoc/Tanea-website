import json
import tempfile
import unittest
from pathlib import Path
from app import app


class ReviewsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'reviews.json'
        self.original = app.config['REVIEWS_FILE']
        app.config['REVIEWS_FILE'] = str(self.path)
        self.client = app.test_client()

    def tearDown(self):
        app.config['REVIEWS_FILE'] = self.original
        self.directory.cleanup()

    def render_reviews(self, entries):
        self.path.write_text(json.dumps(entries), encoding='utf-8')
        return self.client.get('/').get_data(as_text=True)

    def test_empty_or_missing_reviews_hide_section_and_navigation(self):
        for body in (self.client.get('/').get_data(as_text=True), self.render_reviews([])):
            self.assertNotIn('id="avis"', body)
            self.assertNotIn('href="#avis"', body)

    def test_rating_escaping_and_reload(self):
        body = self.render_reviews([dict(author='<Alice>', rating=3, text='<script>avis</script>')])
        self.assertIn('id="avis"', body)
        self.assertEqual(body.count('href="#avis"'), 2)
        self.assertIn('★★★☆☆', body)
        self.assertIn('Note : 3 sur 5', body)
        self.assertIn('&lt;Alice&gt;', body)
        self.assertIn('&lt;script&gt;avis&lt;/script&gt;', body)
        self.assertNotIn('id="avis"', self.render_reviews([]))

    def test_invalid_entries_and_json_do_not_break_page(self):
        invalid = [None, {}, dict(author='A', text='avis', rating=True),
                   dict(author='A', text='avis', rating=6),
                   dict(author=' ', text='avis', rating=4)]
        self.assertNotIn('id="avis"', self.render_reviews(invalid))
        self.assertNotIn('id="avis"', self.render_reviews({'wrong': 'shape'}))
        self.path.write_text('{broken', encoding='utf-8')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'id="avis"', response.data)

    def test_all_star_counts(self):
        for rating in range(1, 6):
            body = self.render_reviews([dict(author='Client', text='Avis test', rating=rating)])
            self.assertIn('★' * rating + '☆' * (5 - rating), body)
