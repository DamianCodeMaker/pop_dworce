import tkinter
from tkinter import *
from tkinter import ttk, messagebox
from geopy.geocoders import Nominatim
import tkintermapview
import time

from ttkthemes import ThemedTk

import math



# --- GŁÓWNA KLASA DANYCH ---
class Entity:
    """Klasa bazowa dla wszystkich obiektów w systemie."""

    def __init__(self, name, app_instance):
        self.name = name
        self.app = app_instance  # Referencja do głównej aplikacji
        self.marker = None
        self.coordinates = None

    def place_marker(self, map_widget, text, coords):
        self.remove_marker()  # Usuń stary marker, jeśli istnieje
        self.coordinates = coords
        if self.coordinates:
            self.marker = map_widget.set_marker(
                self.coordinates[0],
                self.coordinates[1],
                text=text,
                font=("Helvetica", 8),  # Zwiększono czcionkę dla lepszej czytelności
                text_color="white",
                marker_color_circle="black",
                marker_color_outside="gray60",
                command=self.show_details
            )

    def remove_marker(self):
        if self.marker:
            self.marker.delete()
            self.marker = None
            self.coordinates = None  # Współrzędne są powiązane z markerem, więc też je czyścimy

    def show_details(self, marker=None):
        """Metoda wywoływana po kliknięciu znacznika lub przycisku."""
        self.app.show_entity_details(self)

    def __str__(self):
        return self.name

class Station(Entity):
    """Przechowuje dane o dworcu kolejowym."""

    def __init__(self, name, address, app_instance):
        super().__init__(name, app_instance)
        self.address = address
        self.employees = []
        self.carriers = []

    def place_marker(self, map_widget, coords):
        ### ZMIANA: Znacznik dworca pokazuje teraz tylko jego nazwę, bez prefiksu.
        super().place_marker(map_widget, self.name, coords)


class Employee(Entity):
    """Przechowuje dane o pracowniku przypisanym do dworca."""

    def __init__(self, name, position, station, app_instance):
        super().__init__(name, app_instance)
        self.position = position
        self.station = station

class Carrier(Entity):
    """Przechowuje dane o kliencie (przewoźniku) przypisanym do dworca."""

    def __init__(self, name, fleet_type, station, app_instance):
        super().__init__(name, app_instance)
        self.fleet_type = fleet_type
        self.station = station
