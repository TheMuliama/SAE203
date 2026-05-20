CREATE TABLE Catégorie (
    idCat INTEGER PRIMARY KEY,
    nomCat VARCHAR(50)
);

CREATE TABLE Utilisateurs (
    idUser INTEGER PRIMARY KEY, 
    nom VARCHAR(50),
    prenom VARCHAR(50),
    matricule VARCHAR(50)
);

CREATE TABLE Documents (
    idDoc INTEGER PRIMARY KEY, 
    titre VARCHAR(100),
    description VARCHAR(255),
    auteur VARCHAR(50),
    date DATE,
    ressource VARCHAR(50),
    idCat INTEGER,
    idUser INTEGER,
    idMot INTEGER,
    idHist INTEGER,
    FOREIGN KEY (idCat) REFERENCES Catégorie(idCat),
    FOREIGN KEY (idUser) REFERENCES Utilisateurs(idUser)
    FOREIGN KEY (idMot) REFERENCES MotsClés(idMot),
    FOREIGN KEY (idHist) REFERENCES Historique(idHist),
);

CREATE TABLE Historique (
    idHist INTEGER PRIMARY KEY, 
    idDoc INTEGER,              
    date DATE,
    objet VARCHAR(100),
    FOREIGN KEY (idDoc) REFERENCES Documents(idDoc)
);

CREATE TABLE MotsClés (
    idMot INTEGER PRIMARY KEY, 
    mot VARCHAR(50)
);

CREATE TABLE associer (
    idDoc INTEGER,
    idMot INTEGER,
    PRIMARY KEY (idDoc, idMot),
    FOREIGN KEY (idDoc) REFERENCES Documents(idDoc),
    FOREIGN KEY (idMot) REFERENCES MotsClés(idMot)
);