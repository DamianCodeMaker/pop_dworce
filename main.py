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

# --- GŁÓWNA KLASA APLIKACJI ---
class App(ThemedTk):
    def __init__(self):
        super().__init__()
        self.set_theme("arc")

        self.title("Ulepszony System Zarządzania Siecią Dworców")
        self.geometry("1500x900")

        self.all_stations = []
        self.all_employees = []
        self.all_carriers = []
        self.geolocator = Nominatim(user_agent=f"station_mapper_{int(time.time())}")

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=LEFT, fill=Y, padx=(0, 10))
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=LEFT, fill=BOTH, expand=True)

        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=Y, expand=True)

        self.status_var = StringVar()
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=SUNKEN, anchor=W, padding=5)
        status_bar.pack(side=BOTTOM, fill=X)
        self.set_status("Gotowy do pracy.")

        self.create_stations_tab()
        self.create_employees_tab()
        self.create_clients_tab()

        map_frame = ttk.LabelFrame(right_frame, text="Mapa Interaktywna")
        map_frame.pack(fill=BOTH, expand=True)
        self.map_widget = tkintermapview.TkinterMapView(map_frame, width=900, height=800)
        self.map_widget.pack(fill=BOTH, expand=True)
        self.map_widget.set_position(52.23, 21.01)
        self.map_widget.set_zoom(6)

        self.refresh_all()

    def set_status(self, text):
        self.status_var.set(text)

    def get_coords_from_address(self, address):
        try:
            query = address
            if "polska" not in address.lower() and "poland" not in address.lower():
                query = f"{address}, Polska"

            self.set_status(f"Lokalizowanie: {query}...")
            self.update_idletasks()

            location = self.geolocator.geocode(query, timeout=10)

            if location:
                self.set_status("Lokalizacja znaleziona!")
                return [location.latitude, location.longitude]

            self.set_status("Nie znaleziono lokalizacji.")
            return None
        except Exception as e:
            self.set_status(f"Błąd sieci: {e}")
            print(f"Błąd geolokalizacji: {e}")
            return None

    def show_entity_details(self, entity):
        if not entity: return

        title = "Szczegóły Obiektu"
        details = "Brak szczegółów do wyświetlenia."

        if isinstance(entity, Station):
            title = "Szczegóły Dworca"
            details = (f"Nazwa: {entity.name}\n"
                       f"Adres: {entity.address}\n\n"
                       f"Współrzędne: {entity.coordinates}\n"
                       f"Pracownicy: {len(entity.employees)}\n"
                       f"Przewoźnicy: {len(entity.carriers)}")

        elif isinstance(entity, Employee):
            title = "Szczegóły Pracownika"
            details = (f"Imię i Nazwisko: {entity.name}\n"
                       f"Stanowisko: {entity.position}\n\n"
                       f"Dworzec macierzysty: {entity.station.name}\n"
                       f"({entity.station.address})")

        elif isinstance(entity, Carrier):
            title = "Szczegóły Przewoźnika"
            details = (f"Nazwa: {entity.name}\n"
                       f"Typ taboru: {entity.fleet_type}\n\n"
                       f"Dworzec macierzysty: {entity.station.name}\n"
                       f"({entity.station.address})")

        messagebox.showinfo(title, details)

    ### ZMIANA: Nowa metoda do umieszczania znaczników podrzędnych (pracownik/klient) z przesunięciem
    def _place_entity_offset(self, entity):
        """Umieszcza znacznik dla pracownika/klienta z przesunięciem względem dworca."""
        station = entity.station
        if not station.coordinates:
            messagebox.showwarning("Brak lokalizacji", f"Dworzec '{station.name}' nie ma współrzędnych na mapie.")
            return

        # Zlicz, ile już jest widocznych znaczników dla tego dworca (oprócz samego dworca)
        visible_children_count = 0
        for emp in station.employees:
            if emp.marker:
                visible_children_count += 1
        for car in station.carriers:
            if car.marker:
                visible_children_count += 1

        # Oblicz przesunięcie, aby znaczniki nie nakładały się na siebie
        # Można dostosować promień i kąt do własnych preferencji
        radius = 0.0005 * (1 + (visible_children_count // 8))  # Zwiększ promień co 8 znaczników
        angle = (visible_children_count * 45) % 360  # Kąt co 45 stopni
        angle_rad = math.radians(angle)

        # Oblicz nowe współrzędne
        lat_offset = radius * math.cos(angle_rad)
        lon_offset = radius * math.sin(angle_rad)

        new_coords = [station.coordinates[0] + lat_offset, station.coordinates[1] + lon_offset]

        # Ustal tekst dla znacznika
        if isinstance(entity, Employee):
            text = f"Pracownik:\n{entity.name}"
        elif isinstance(entity, Carrier):
            text = f"Przewoźnik:\n{entity.name}"
        else:
            text = entity.name

        entity.place_marker(self.map_widget, text, new_coords)
        self.set_status(f"Pokazano na mapie: {entity.name}")