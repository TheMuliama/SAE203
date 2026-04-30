import sys
# Éléments d'interface
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, 
                             QLabel, QPushButton, QHeaderView)
# Logique de base et signaux
from PyQt6.QtCore import (Qt, QTimer, QObject) 
# Pour le visuel
from PyQt6.QtGui import (QIcon, QPixmap, QColor, QAction) 


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Création de la fenêtre
        self.setWindowTitle("SAE 203 - Gestion documentaire")
        self.setWindowIcon(QIcon("pouce.png"))
        self.resize(1100, 700)

        self.createActions()
        self.createMenuBar()

        # Bas de l'appli
        statusBar = self.statusBar()
        statusBar.showMessage(self.windowTitle())

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout(central_widget)

        # On crée un conteneur pour la partie gauche de l'appli
        left_container = QWidget() 
        left_layout = QVBoxLayout(left_container)
        
        # La barre de recherche
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Rechercher un document...")
        left_layout.addWidget(self.search_bar)
        self.table = QTableWidget(30, 4)
        self.table.setHorizontalHeaderLabels(["Titre", "Auteur", "Date", "Catégorie"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.table)
        
        # Ajout de la partie gauche avec un gros stretch (4) pour qu'elle soit longue
        main_layout.addWidget(left_container, stretch=4)

        # On crée la partie droite (détails)
        right_panel = QWidget()
        right_panel.setStyleSheet("border-left: 1px solid #ddd;")
        right_layout = QVBoxLayout(right_panel)
        
        # Texte de la partie détails
        right_layout.addWidget(QLabel("<b>Détails</b>"))
        right_layout.addWidget(QLabel("Titre : "))
        right_layout.addWidget(QLabel("Auteur : "))
        right_layout.addWidget(QLabel("Date : "))
        right_layout.addWidget(QLabel("Catégorie : "))
        right_layout.addWidget(QLabel("Type : "))
        right_layout.addWidget(QLabel("Mots-clés : "))
        right_layout.addWidget(QLabel("Description : "))
        
        # Le stretch est placé ici pour ne pas faire monter les boutons vers le milieu
        right_layout.addStretch(2) # Il fait monter le texte
        # Ce stretch crée un espace avant les boutons
        right_layout.addSpacing(20) 
        
        # Layout horizontal pour les boutons côte à côte
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("Ouvrir"))
        btn_layout.addWidget(QPushButton("Télécharger"))
        btn_layout.setSpacing(10) 
        right_layout.addLayout(btn_layout)
                
        # On ajoute la partie droite au layout principal
        main_layout.addWidget(right_panel, stretch=2)

    def createActions(self):
        self.actNew = QAction(QIcon("assets/icons/papier.png"), "&Nouveau", self)
        self.actNew.setShortcut("Ctrl+N")
        self.actNew.setStatusTip("Nouveau Document")
        self.actNew.triggered.connect(self.newDocument)

        self.actOpen = QAction(QIcon("assets/icons/ouvrir.png"), "&Ouvrir...", self)
        self.actOpen.setShortcut("Ctrl+O")
        self.actOpen.setStatusTip("Ouvrir un fichier")
        self.actOpen.triggered.connect(self.openDocument)

        self.actExit = QAction(QIcon("assets/icons/quitter.png"), "Quitter", self)
        self.actExit.setShortcut("Alt+F4")
        self.actExit.setStatusTip("Quitter")
        self.actExit.triggered.connect(self.quitApp)

    def createMenuBar(self):
        # Barre du menu
        # Partie pour Fichier
        menu = self.menuBar()
        file = menu.addMenu("&File")
        file.addAction(self.actNew)
        file.addSeparator()
        file.addAction(self.actOpen)
        file.addSeparator()
        file.addAction(self.actExit)

        # Partie pour le reste
        file_menu = menu.addMenu("Édition")
        file_menu.addAction("Exporter")
        file_menu.addAction("Modifier un document")
        file_menu.addAction("Supprimer un document")
        file_menu = menu.addMenu("Importer")
        file_menu.addAction("Sélectionner un document")
        file_menu = menu.addMenu("Aide")
        file_menu.addAction("tar")

    def newDocument(self):
        print("Nouveau document demandé")
        self.statusBar().showMessage("Nouveau document créé", 3000)

    def openDocument(self):
        print("Action : Ouvrir document")

    def quitApp(self):
        self.close()

def main():
    app = QApplication(sys.argv)    
    window = MainWindow()
    #window.changeColor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()