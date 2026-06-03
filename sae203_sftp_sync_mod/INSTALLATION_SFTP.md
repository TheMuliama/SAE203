# Intégration SFTP - SAE203 / SoweDrop

## Fichiers à remplacer / ajouter

Copier ces fichiers dans le projet :

- `src/interface.py` remplace le fichier existant.
- `src/sftp_storage.py` est un nouveau fichier.
- `requirements.txt` remplace le fichier existant.
- `.gitignore` remplace ou complète le fichier existant.
- `data/private/sftp_config.example.json` est un modèle de configuration.

## Configuration SFTP

Créer le fichier réel de configuration :

```bash
mkdir -p data/private
cp data/private/sftp_config.example.json data/private/sftp_config.json
nano data/private/sftp_config.json
```

Modifier le mot de passe :

```json
{
  "host": "51.210.247.212",
  "port": 22,
  "username": "user1",
  "password": "TON_MOT_DE_PASSE_USER1",
  "remote_base": "/commun"
}
```

Le fichier `data/private/sftp_config.json` ne doit pas être envoyé sur GitHub.

## Installer la dépendance SFTP

```bash
.venv/bin/pip install paramiko
```

Ou :

```bash
pip install -r requirements.txt
```

## Tester

```bash
python main.py
```

Dans l'application :

1. Ajouter un document.
2. Choisir le stockage `partage`.
3. Valider.
4. Vérifier sur le VPS ou dans FileZilla que le fichier arrive dans `/commun`.
5. Tester le bouton `Ouvrir`.
6. Tester le bouton `Télécharger`.

## Fonctionnement

- Stockage `local` : copie le fichier dans `data/documents/local/`.
- Stockage `partage` : envoie le fichier sur le VPS en SFTP dans `/commun`.
- Le chemin enregistré en base ressemble à :

```text
sftp:/commun/abcd1234_document.pdf
```

Quand on ouvre ou télécharge un fichier distant, il est d'abord récupéré dans :

```text
data/documents/cache/
```
