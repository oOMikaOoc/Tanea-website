import unittest
from urllib.parse import parse_qs, urlparse

from app import app


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        import app as app_module
        app_module._submissions.clear()
        self.data = dict(name='Éloïse Martin', phone='+33 6 12 34 56 78',
                         service='Broderie', message='Deux sweats crème & dorés\npour un anniversaire.')
        with self.client.get('/') as response:
            import re
            self.csrf = re.search(rb'name="_csrf_token" value="([^"]+)"', response.data).group(1).decode()

    def test_page_and_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Atelier de'.encode(), response.data)
        for image in ('tanea-logo.png', 'atelier-creations.png'):
            response = self.client.get('/static/images/' + image)
            self.assertEqual(response.status_code, 200)
            response.close()

    def test_whatsapp_message(self):
        for service in ('Broderie', 'Flocage DTF', 'Sublimation', 'Autre'):
            response = self.client.post('/contact', data={**self.data, 'service': service, '_csrf_token': self.csrf})
            self.assertEqual(response.status_code, 303)
            url = urlparse(response.location)
            self.assertEqual((url.scheme, url.netloc, url.path), ('https', 'wa.me', '/33621764499'))
            message = parse_qs(url.query)['text'][0]
            for value in (self.data['name'], self.data['phone'], self.data['message'], service):
                self.assertIn(value, message)

    def test_invalid_and_empty_fields(self):
        for key, value in [('name', ''), ('phone', 'not-a-phone'), ('service', 'unexpected'), ('message', 'court'), ('message', 'x' * 1501)]:
            response = self.client.post('/contact', data={**self.data, key: value, '_csrf_token': self.csrf})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn('Location', response.headers)
        self.assertIn(self.client.post('/contact', data={'_csrf_token': self.csrf}).status_code, (422, 429))

    def test_html_is_escaped_and_values_preserved(self):
        response = self.client.post('/contact', data={**self.data, 'name': '<script>alert(1)</script>', 'phone': '', '_csrf_token': self.csrf})
        self.assertNotIn(b'<script>alert(1)</script>', response.data)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertIn('Deux sweats crème'.encode(), response.data)

    def test_limits_and_method(self):
        self.assertEqual(self.client.get('/contact').status_code, 405)
        self.assertEqual(self.client.post('/contact', data={'message': 'x' * 20000, '_csrf_token': self.csrf}).status_code, 413)

    def test_csrf_and_rate_limit(self):
        self.assertEqual(self.client.post('/contact', data=self.data).status_code, 400)
        app.config['TESTING'] = True
        for _ in range(5):
            self.client.post('/contact', data={**self.data, '_csrf_token': self.csrf}, environ_base={'REMOTE_ADDR': 'rate-test'})
        response = self.client.post('/contact', data={**self.data, '_csrf_token': self.csrf}, environ_base={'REMOTE_ADDR': 'rate-test'})
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response.headers)


if __name__ == '__main__':
    unittest.main()
