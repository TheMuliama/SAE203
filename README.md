# ... | SAE 2.03 - Groupe 9

## Présentation du Projet
... est une application desktop développée en **Python** avec **PyQt6**. Elle permet de centraliser, indexer et retrouver rapidement des documents professionnels grâce à un système de métadonnées stockées en base **SQLite**.

## Guide d'utilisation de Git
### 1. Prérequis
Avant toute chose, tu dois avoir **Git** installé sur sa machine.
* [Télécharger Git ici](https://git-scm.com/downloads)
### 2. Configuration initiale
Avant toute contribution, configurez votre identité locale pour signer vos commits.
```bash
git config --global user.name "VotrePseudo"
git config --global user.email "email@exemple.com"
```
### 3. Initialisation du dépôt
Ouvre un terminal (ou Git Bash) dans ton dossier de travail et tape :
```bash 
git clone [https://github.com/TheMuliama/SAE203.git](https://github.com/TheMuliama/SAE203.git) # Clonage du dépôt distant
```
```bash
cd SAE203 # Accès au répertoire du projet
```
### 4. Synchronisation
On récupère le travail des autres pour être à jour : 
```bash 
git pull origin main
```
### 5. Indexation et Commit
On prépare les fichiers que l'on veut envoyer : 
```bash 
git add .
```
Détailler et expiquer ce que vous avez fait : 
```bash 
git commit -m "Ajout du bouton valider dans interface.py"
```
### 6. Déploiement
Sauvegarde et affichage du travail sur le projet : 
```bash
git push origin main
```


## Lancement
```bash
python main.py
```
