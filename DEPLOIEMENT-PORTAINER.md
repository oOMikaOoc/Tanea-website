# TANÉA — Déploiement Portainer

Cible : serveur Linux, Docker Standalone (pas Swarm). Si ton serveur Portainer dispose de ressources suffisantes, seul le nom de domaine est à acheter ; un deuxième hébergement n’est pas nécessaire.

## 1. Publier l’image sur GHCR

Placer ce projet, y compris `.github/workflows/ghcr.yml`, dans le dépôt GitHub choisi. Le dossier livré ne contient actuellement ni dépôt Git ni remote configuré. GitHub Actions doit être autorisé sur le dépôt.

Le workflow exécute les tests puis construit pour Linux amd64 et arm64. Les pushes sur main/master, les tags v* et le lancement manuel publient sur `ghcr.io/<proprietaire>/<depot>` (en minuscules). Les pull requests vérifient la construction sans publier. L'authentification utilise automatiquement GITHUB_TOKEN avec packages:write ; aucun secret GHCR à ajouter pour la publication.

La branche par défaut reçoit `latest`. Chaque construction reçoit `sha-<SHA complet>` ; un tag Git `v1.0.0` produit également le tag d'image `v1.0.0`. Pour Portainer, préférer un tag de version ou un digest `@sha256:...` et conserver la référence précédente pour revenir en arrière.

Attendre le succès du workflow et vérifier le package dans GitHub avant de déployer. Si le package est privé, ajouter dans Portainer > Registries un registre personnalisé `ghcr.io`, avec le nom d'utilisateur GitHub et un personal access token (classic) disposant de `read:packages` (autoriser le SSO de l'organisation si nécessaire). Ne jamais mettre ce jeton dans le compose ou dans Git. Un package public peut être téléchargé sans authentification.

### Alternative : construction locale sur le serveur

Si nécessaire, transférer les sources sur le serveur Docker géré par Portainer, puis :

~~~sh
mkdir -p tanea-deploy
tar -xzf tanea-portainer.tar.gz -C tanea-deploy
cd tanea-deploy
docker build -t tanea:1.0.0 .
~~~

Dans ce mode local uniquement, définir TANEA_IMAGE=tanea:1.0.0 et remplacer pull_policy: always par pull_policy: never dans la stack. Le Dockerfile doit être accompagné des sources, templates, images et données.

## 2. Créer le volume

Portainer > Volumes > Add volume : nom exact tanea_data, pilote local. Le volume externe conserve son existence indépendamment de la stack.

Au premier démarrage avec un volume vide, Docker y copie /app/data/reviews.json, initialement []. Les avis existants restent ensuite conservés lors des mises à jour. Sauvegarder le volume séparément.

Le site monte /app/data en lecture seule. Modifier reviews.json via un outil de gestion de volumes ou un conteneur temporaire monté en écriture. Conserver le fichier lisible par l’utilisateur non root (fichier 644, dossier 755). Le site relit les avis au prochain affichage. Aucun formulaire n’est stocké dans ce volume.

## 3. Déployer

Portainer > Stacks > Add stack, nom tanea, Web editor : coller compose.yaml.

Ajouter dans Environment variables :

| Variable | Valeur |
|---|---|
| TANEA_IMAGE | Référence publiée, par exemple ghcr.io/proprietaire/depot:v1.0.0 ; remplacer par le vrai nom en minuscules |
| FLASK_SECRET_KEY | Clé aléatoire persistante, 64 caractères hexadécimaux |
| FLASK_COOKIE_SECURE | true pour HTTPS ; false uniquement pendant un essai HTTP local |
| TANEA_PORT | 8085, modifiable si le port est occupé |

Générer la clé sur le serveur :

~~~sh
openssl rand -hex 32
~~~

Conserver la clé pour les redéploiements. Ne pas la publier dans Git. Sélectionner le registre GHCR configuré si l'image est privée. La stack télécharge l'image publiée. Cliquer Deploy the stack et vérifier que le conteneur devient healthy.

## 4. Tester avant Cloudflare

Le port est lié uniquement à 127.0.0.1 du serveur. Sur le serveur :

~~~sh
curl -I http://127.0.0.1:8085/
~~~

Pour consulter depuis ton ordinateur, adapter et lancer :

~~~sh
ssh -L 8085:127.0.0.1:8085 utilisateur@serveur
~~~

Puis ouvrir http://localhost:8085. Pour cet essai HTTP, mettre FLASK_COOKIE_SECURE=false et redéployer afin que le formulaire puisse utiliser son cookie de session. Repasser à true pour le domaine HTTPS.

Après raccordement HTTPS, essayer le formulaire depuis un téléphone : WhatsApp doit s’ouvrir vers le 06 21 76 44 99 avec la demande préremplie. Le client doit ensuite appuyer sur Envoyer. Aucune API WhatsApp à configurer.

## 5. Raccorder Cloudflare ensuite

Le réseau Docker tanea_proxy est créé par la stack. Un conteneur cloudflared ou reverse proxy pourra rejoindre ce réseau et utiliser http://tanea:8000. Un proxy installé directement sur le serveur utilisera http://127.0.0.1:8085.

Le montage sera adapté à celui de Hack and Craft. Aucun jeton Cloudflare ni domaine fictif n’est inclus. Ne pas mettre en cache les pages HTML ni /contact : elles utilisent une session. Les fichiers /static/ peuvent être mis en cache.

Avant ouverture au public, adapter la récupération de l’IP au type et au nombre exacts de proxies de confiance : actuellement request.remote_addr peut représenter le proxy, ce qui ferait partager la limite de 5 demandes par heure à plusieurs visiteurs. Ne pas faire confiance sans contrôle à un en-tête IP reçu d’Internet.

Un seul worker Gunicorn avec quatre threads partage la limite en mémoire entre les requêtes. Elle se réinitialise au redémarrage ; ne pas multiplier les réplicas sans stockage partagé. Le site n’a pas besoin de Redis ou de base de données pour cette première stack.

## 6. Mettre à jour

Publier un nouveau tag Git (exemple v1.0.1), attendre le succès du workflow, changer TANEA_IMAGE dans Portainer pour la référence GHCR correspondante, puis redéployer. Conserver FLASK_SECRET_KEY et tanea_data. Pour revenir en arrière, remettre la référence précédente. Le JSON d’une nouvelle image ne remplace pas celui d’un volume déjà rempli.

Restent avant publication : mentions légales, information sur les données du formulaire, domaine/HTTPS, configuration de l’IP client et essai réel WhatsApp.

## Validation

Le moteur Docker n’est pas disponible sur le poste de préparation : construction et démarrage de la stack à valider sur le serveur Portainer. Les tests applicatifs sont exécutés séparément.

Références :
- https://docs.portainer.io/user/docker/stacks/add
- https://docs.portainer.io/user/docker/images/build
- https://docs.docker.com/engine/storage/volumes/
