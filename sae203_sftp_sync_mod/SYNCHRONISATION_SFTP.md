# Synchronisation SFTP des documents partagés

## Problème corrigé

Avant cette modification, l'application envoyait bien le fichier dans `/commun` sur le VPS, mais l'autre application ne le voyait pas car sa base SQLite locale ne contenait pas les métadonnées du document.

## Solution ajoutée

Quand un document est ajouté avec le stockage `partage` :

1. le fichier est envoyé sur le VPS en SFTP ;
2. l'application ajoute le document dans sa base SQLite locale ;
3. l'application envoie aussi un fichier JSON de métadonnées à côté du fichier.

Exemple sur le serveur :

```text
/commun/
├── a1b2c3d4_rapport.pdf
└── a1b2c3d4_rapport.pdf.json
```

Le fichier JSON contient le titre, l'auteur, la date, la description, les catégories, les mots-clés et le chemin SFTP du fichier.

## Synchronisation depuis une autre application

L'autre application peut maintenant récupérer les documents partagés :

- automatiquement au démarrage ;
- manuellement depuis le menu :

```text
Importer > Synchroniser les documents partagés
```

ou avec le raccourci :

```text
Ctrl + R
```

La synchronisation :

1. lit les fichiers `.json` dans `/commun` ;
2. vérifie les documents déjà présents dans la base SQLite locale ;
3. ajoute uniquement les documents manquants ;
4. recharge la liste des documents.

## Fichiers modifiés

- `src/sftp_storage.py`
- `src/interface.py`

## Test conseillé

Sur le poste 1 :

1. lancer l'application ;
2. ajouter un document ;
3. choisir `partage` ;
4. vérifier dans FileZilla que le fichier et le `.json` sont présents dans `/commun`.

Sur le poste 2 :

1. lancer l'application ;
2. aller dans `Importer > Synchroniser les documents partagés` ;
3. vérifier que le document apparaît dans la liste ;
4. tester `Ouvrir` ou `Télécharger`.
