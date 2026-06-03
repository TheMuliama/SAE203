# Suppression des documents partagés sur le VPS

Cette modification ajoute la suppression distante des documents partagés.

Quand un document dont la ressource commence par `sftp:` est supprimé depuis l'application :

1. l'application supprime le fichier réel sur le VPS ;
2. l'application supprime aussi le fichier `.json` de métadonnées associé ;
3. l'entrée du document est ensuite supprimée de la base SQLite locale.

Exemple :

```text
sftp:/commun/abc123_rapport.pdf
```

La suppression retire :

```text
/commun/abc123_rapport.pdf
/commun/abc123_rapport.pdf.json
```

## Fichiers à remplacer

```bash
cp sae203_delete_vps_mod/src/interface.py src/interface.py
cp sae203_delete_vps_mod/src/sftp_storage.py src/sftp_storage.py
```

## Test

1. Ajouter un document en stockage `partage`.
2. Vérifier sur le VPS que le fichier et le `.json` existent dans `/commun`.
3. Supprimer le document depuis l'application.
4. Vérifier sur le VPS que les deux fichiers ont disparu.

```bash
ls -la /srv/sftp/commun
```
