# TANÉA — atelier de personnalisation à Gap

Landing page Python / Flask, Jinja2, Tailwind CSS via CDN, icônes SVG intégrées et Google Fonts. Logo officiel fourni et visuel d’ambiance local. Mise en page responsive, navigation mobile, formulaire avec validation côté serveur.

## Démarrage local

```sh
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux : source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Ouvrir http://localhost:5000. `PORT` permet de choisir un autre port. Le serveur de développement fonctionne sans mode debug ; utiliser le conteneur pour servir avec Gunicorn.

## Conteneur Flask

```sh
docker build -t tanea .
docker run --rm -p 8000:8000 tanea
```

Ouvrir http://localhost:8000 pour un essai local. En production, définir FLASK_SECRET_KEY avec une clé persistante ; aucune base de données nécessaire. Pour Portainer, suivre DEPLOIEMENT-PORTAINER.md et compose.yaml.

## Fonctionnement

- `GET /` affiche `templates/index.html`.
- `POST /contact` valide `name`, `phone`, `service`, `message` et répond par une redirection HTTP 303 vers `https://wa.me/33621764499?text=...`.
- Le formulaire contient un jeton CSRF signé par la session Flask, un champ honeypot invisible et une limite de 5 soumissions par adresse IP sur 1 heure. Un dépassement répond HTTP 429 avec `Retry-After`; la limite est conservée en mémoire du processus (pour plusieurs workers, utiliser un stockage partagé comme Redis ou un reverse proxy).
- Définir `FLASK_SECRET_KEY` avec une valeur aléatoire persistante en production. `SESSION_COOKIE_HTTPONLY` et `SameSite=Lax` sont activés ; définir `FLASK_COOKIE_SECURE=true` derrière HTTPS.
- Le texte est encodé avec `urllib.parse.urlencode`, y compris accents, esperluettes et sauts de ligne.
- Une demande invalide réaffiche la page avec les champs conservés et un statut 422. Une requête supérieure à 16 Ko renvoie 413.
- Aucune demande n’est enregistrée ni envoyée automatiquement. Le client confirme l’envoi dans WhatsApp. Les informations du formulaire sont incluses dans l’URL WhatsApp ; elles peuvent donc apparaître dans l’historique du navigateur. Déployer avec HTTPS et ne pas journaliser les corps des requêtes ou les en-têtes Location.
- Les liens de prestation présélectionnent le menu du formulaire. Le formulaire fonctionne sans JavaScript.

## Avant publication

Les avis se gèrent dans `data/reviews.json` (voir ci-dessous). Aucun score ni avis n’est déclaré aux moteurs de recherche. Ajouter les mentions légales avec les informations réelles de l’entreprise avant publication. L’identifiant TikTok fourni est affiché tel quel : ajouter son URL officielle une fois vérifiée.

Tailwind et les polices nécessitent une connexion Internet ; les règles CSS essentielles sont également intégrées à la page. Pour une diffusion en production sans CDN, compiler Tailwind et héberger les polices localement.

## Visuels

- `static/images/tanea-logo.png` : logo officiel fourni, conservé sans modification.
- `static/images/atelier-creations.png` : visuel d’inspiration généré avec l’outil intégré ImageGen ; ce n’est pas une photographie de réalisations réelles de l’atelier. La légende le précise.

Prompt du visuel : photographie éditoriale réaliste en format paysage sur lin crème, sweat coton crème plié avec petite broderie botanique terracotta, mug ivoire au motif assorti, décoration en bois gravée et bobines ocre. Lumière naturelle douce, matières détaillées, palette crème #F8F3EC, terracotta #C05638 et ocre #D8A562. Aucun texte, logo, filigrane ou personnage.

## Vérification

```sh
python -m unittest discover -s tests -v
```

Tests : page et images, quatre prestations, destination WhatsApp fixe, encodage du message, erreurs, échappement HTML et limite de taille.

## Avis clients

Le fichier `data/reviews.json` contient une liste d’avis et démarre vide (`[]`). La section et les liens « Avis » sont masqués tant qu’aucun avis valide n’est disponible. Les modifications sont prises en compte au prochain chargement de la page, sans redémarrage.

Pour ajouter un avis copié depuis Google, remplacer `[]` par une liste au format suivant (exemple de structure à remplacer par un véritable avis) :

```json
[
  {
    "author": "Nom affiché sur Google",
    "rating": 4,
    "text": "Copier ici le texte exact de l’avis."
  }
]
```

`rating` est un entier de 1 à 5 : les étoiles pleines et vides suivent cette note. Ajouter les avis à la suite, séparés par une virgule. Auteur et texte sont obligatoires. Les entrées invalides sont ignorées ; un fichier absent ou un JSON incorrect masque les avis sans bloquer la page. Les textes sont échappés à l’affichage.
