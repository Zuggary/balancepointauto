"""Offline structural and preservation checks; no browser or network required."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def protected_html(text):
    text = re.sub(r'<script\b[^>]*>.*?</script>', '', text, flags=re.S)
    return text.replace(' tabindex="-1"', '')


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class StaticAudit(unittest.TestCase):
    def test_original_content_and_styles(self):
        manifest = json.loads((ROOT / 'tests/preservation.json').read_text())
        for name, expected in manifest.items():
            with self.subTest(file=name):
                text = (ROOT / name).read_text()
                if name.endswith('.html'):
                    text = protected_html(text)
                self.assertEqual(digest(text), expected)

    def test_counter_unchanged(self):
        text = (ROOT / 'index.html').read_text()
        counter = text[text.index('  // ---- anonymous visit counter'):]
        expected = (ROOT / 'tests/counter.sha256').read_text().strip()
        self.assertEqual(digest(counter), expected)

    def test_skip_links_have_focusable_main(self):
        for page in ROOT.glob('*.html'):
            with self.subTest(page=page.name):
                doc = Document(page.read_text())
                mains = [a for tag, a in doc.elements if tag == 'main']
                self.assertEqual(len(mains), 1)
                self.assertEqual(mains[0].get('id'), 'main')
                self.assertEqual(mains[0].get('tabindex'), '-1')
                self.assertTrue(any(tag == 'a' and a.get('href') == '#main'
                                    for tag, a in doc.elements))

    def test_static_ids_and_accessibility_references(self):
        for page in ROOT.glob('*.html'):
            with self.subTest(page=page.name):
                doc = Document(page.read_text())
                ids = [a['id'] for _, a in doc.elements if 'id' in a]
                self.assertEqual(len(ids), len(set(ids)))
                for _, attrs in doc.elements:
                    for key in ('aria-labelledby', 'aria-describedby', 'for'):
                        for reference in attrs.get(key, '').split():
                            self.assertIn(reference, ids)


if __name__ == '__main__':
    unittest.main()
