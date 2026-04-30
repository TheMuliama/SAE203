import sys
from PyQt6.QtWidgets import QApplication
from src.interface import FenetrePrincipale

if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenetre = FenetrePrincipale()
    fenetre.show()
    sys.exit(app.exec())
