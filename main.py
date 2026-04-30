import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QPushButton, QHeaderView)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAE 203 - Gestion documentaire")
        self.resize(1100, 700)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout(central_widget)

        # --- PARTIE GAUCHE : RECHERCHE ET TABLEAU ---
        left_container = QWidget() # On crée un conteneur pour la gauche
        left_layout = QVBoxLayout(left_container)
        
        # La barre de recherche
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Rechercher un document...")
        left_layout.addWidget(self.search_bar)

        self.table = QTableWidget(10, 4)
        self.table.setHorizontalHeaderLabels(["Titre", "Auteur", "Date", "Catégorie"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.table)
        
        # Ajout de la partie gauche avec un gros stretch (4) pour qu'elle soit longue
        main_layout.addWidget(left_container, stretch=4)

        # --- PARTIE DROITE : DÉTAILS ---
        right_panel = QWidget()
        right_panel.setStyleSheet("border-left: 1px solid #ddd;")
        right_layout = QVBoxLayout(right_panel)
        
        # 1. Premier stretch pour décoller le texte du haut de la fenêtre
        right_layout.addStretch(1) 
        
        # 2. Texte de la partie détail
        right_layout.addWidget(QLabel("<b>Détails</b>"))
        right_layout.addWidget(QLabel("Titre : "))
        right_layout.addWidget(QLabel("Auteur : "))
        right_layout.addWidget(QLabel("Date : "))
        right_layout.addWidget(QLabel("Catégorie : "))
        right_layout.addWidget(QLabel("Type : "))
        right_layout.addWidget(QLabel("Mots-clés : "))
        right_layout.addWidget(QLabel("Description : "))
        
        # Le stretch est placé ici pour ne pas faire monter les boutons vers le milieu
        right_layout.addStretch(2)
        # 3. Ce stretch "moyen" (0.5) crée un petit espace avant les boutons
        right_layout.addSpacing(20) 
        
        # 4. Layout horizontal pour les boutons côte à côte
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton("Ouvrir"))
        btn_layout.addWidget(QPushButton("Télécharger"))
        btn_layout.setSpacing(10) 
        
        right_layout.addLayout(btn_layout)
                
        # On ajoute la partie droite au layout principaaaaaal
        main_layout.addWidget(right_panel, stretch=2)

    def changeColor(self):
        self.setStyleSheet("""  QMainWindow { background-color: white; }
                                QLabel { color: black; } 
                                QLineEdit { color: #a3a3a3; }
                                QHBoxLayout { color: white; gridline-color: white; }
                                QTableWidget { background-color: silver; gridline-color: white; color: black; } 
                                QPushButton { color: black; background-color: #a3a3a3 } """)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.changeColor()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
