import os
import json
import re
import secrets
import threading
import time
import hmac
from datetime import date
from urllib.parse import urlencode

from flask import Flask, redirect, render_template, request, session

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_COOKIE_SECURE', '').lower() == 'true'
app.config['REVIEWS_FILE'] = os.path.join(app.root_path, 'data', 'reviews.json')
SERVICES = ('Broderie', 'Flocage DTF', 'Sublimation', 'Autre')
RATE_LIMIT = 5
RATE_WINDOW = 3600
_rate_lock = threading.Lock()
_submissions = {}


def csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


@app.context_processor
def inject_csrf():
    return {'csrf_token': csrf_token}



def load_reviews():
    """Relit les avis à chaque affichage ; ignore les entrées incomplètes."""
    try:
        with open(app.config['REVIEWS_FILE'], encoding='utf-8') as review_file:
            entries = json.load(review_file)
    except (OSError, ValueError):
        app.logger.warning('Fichier des avis absent ou illisible.')
        return []
    if not isinstance(entries, list):
        return []
    reviews = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        author, text, rating = (entry.get(key) for key in ('author', 'text', 'rating'))
        if (not isinstance(author, str) or not author.strip()
                or not isinstance(text, str) or not text.strip()
                or type(rating) is not int or not 1 <= rating <= 5):
            continue
        reviews.append(dict(author=author.strip(), text=text.strip(), rating=rating))
    return reviews


def page(values=None, errors=None):
    return render_template('index.html', services=SERVICES, reviews=load_reviews(),
                           values=values or {}, errors=errors or {}, year=date.today().year)


@app.get('/')
def index():
    return page()


@app.post('/contact')
def contact():
    sent_token = request.form.get('_csrf_token', '')
    expected_token = session.get('_csrf_token', '')
    if not expected_token or not sent_token or not hmac.compare_digest(sent_token, expected_token):
        return page(errors={'form': 'Votre session a expiré. Rechargez la page puis réessayez.'}), 400
    # Champ invisible : les soumissions de robots sont écartées avant tout traitement.
    if request.form.get('website', '').strip():
        return page(errors={'form': 'Votre demande n’a pas pu être traitée.'}), 400
    now = time.monotonic()
    client_key = request.remote_addr or 'unknown'
    with _rate_lock:
        attempts = [stamp for stamp in _submissions.get(client_key, []) if now - stamp < RATE_WINDOW]
        if len(attempts) >= RATE_LIMIT:
            retry_after = max(1, int(RATE_WINDOW - (now - attempts[0])))
            response = page(errors={'form': 'Trop de demandes depuis cette adresse. Réessayez plus tard.'}), 429
            response = app.make_response(response)
            response.headers['Retry-After'] = str(retry_after)
            return response
        attempts.append(now)
        _submissions[client_key] = attempts
    values = {key: request.form.get(key, '').strip()
              for key in ('name', 'phone', 'service', 'message')}
    errors = {}
    if not 2 <= len(values['name']) <= 100 or any(c in values['name'] for c in '\r\n'):
        errors['name'] = 'Indiquez votre nom (2 à 100 caractères).'
    phone = values['phone']
    if not re.fullmatch(r'\+?[0-9 .()\-]+', phone) or not 8 <= len(re.sub(r'\D', '', phone)) <= 15:
        errors['phone'] = 'Indiquez un numéro de téléphone valide.'
    if values['service'] not in SERVICES:
        errors['service'] = 'Choisissez une prestation dans la liste.'
    if not 10 <= len(values['message']) <= 1500:
        errors['message'] = 'Décrivez votre projet en 10 à 1 500 caractères.'
    if errors:
        return page(values, errors), 422
    message = (
        'Bonjour Tania ! Je souhaite un devis pour un projet TANÉA.\n\n'
        f"Nom : {values['name']}\n"
        f"Téléphone : {phone}\n"
        f"Prestation : {values['service']}\n\n"
        f"Mon projet :\n{values['message']}\n\nMerci et à bientôt !"
    )
    return redirect('https://wa.me/33621764499?' + urlencode({'text': message}), code=303)


@app.errorhandler(413)
def too_large(_error):
    return page(errors={'form': 'Votre demande est trop longue. Merci de raccourcir votre message.'}), 413


@app.errorhandler(429)
def too_many_requests(_error):
    return page(errors={'form': 'Trop de demandes. Réessayez plus tard.'}), 429


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')), debug=False)
