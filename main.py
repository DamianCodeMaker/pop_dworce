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

# --- ZAKŁADKA DWORCE ---
    def create_stations_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Dworce")

        form = ttk.LabelFrame(tab, text="Formularz Dworca", padding=10)
        form.pack(fill=X)
        ttk.Label(form, text="Nazwa Dworca:").grid(row=0, column=0, sticky=W, padx=5, pady=3)
        self.station_name_entry = ttk.Entry(form)
        self.station_name_entry.grid(row=0, column=1, sticky=EW, padx=5, pady=3)
        ttk.Label(form, text="Miasto i/lub Adres:").grid(row=1, column=0, sticky=W, padx=5, pady=3)
        self.station_address_entry = ttk.Entry(form)
        self.station_address_entry.grid(row=1, column=1, sticky=EW, padx=5, pady=3)
        self.station_add_btn = ttk.Button(form, text="Dodaj Dworzec", command=self.add_station)
        self.station_add_btn.grid(row=2, column=0, columnspan=2, pady=10)
        form.columnconfigure(1, weight=1)

        list_frame = ttk.LabelFrame(tab, text="Lista Dworców", padding=10)
        list_frame.pack(fill=BOTH, expand=True, pady=10)
        self.stations_listbox = Listbox(list_frame, font=("Helvetica", 9), relief=SUNKEN, bd=1)
        self.stations_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=LEFT, fill=Y, padx=5)
        ttk.Button(btn_frame, text="Pokaż na Mapie", command=self.focus_on_selected_station).pack(pady=2)
        ttk.Button(btn_frame, text="Usuń Zaznaczony", command=self.remove_station).pack(pady=2)

    def add_station(self):
        name = self.station_name_entry.get()
        address = self.station_address_entry.get()
        if not name or not address:
            messagebox.showerror("Błąd", "Nazwa i adres są wymagane.")
            return

        full_query = f"{name}, {address}"
        coords = self.get_coords_from_address(full_query)
        if not coords:
            messagebox.showerror("Błąd", f"Nie udało się zlokalizować: {full_query}")
            return

        station = Station(name, address, self)
        station.place_marker(self.map_widget, coords)  # Znacznik dworca jest umieszczany od razu
        self.all_stations.append(station)
        self.map_widget.set_position(coords[0], coords[1], marker=False)
        self.map_widget.set_zoom(16)

        self.refresh_all()
        self.station_name_entry.delete(0, END)
        self.station_address_entry.delete(0, END)

    def remove_station(self):
        selected = self.stations_listbox.curselection()
        if not selected: return

        if messagebox.askyesno("Potwierdzenie",
                               "Czy na pewno chcesz usunąć ten dworzec i wszystkie powiązane obiekty?"):
            station = self.all_stations[selected[0]]

            # Usuń znaczniki powiązanych obiektów
            for emp in station.employees: emp.remove_marker()
            for car in station.carriers: car.remove_marker()

            # Usuń znacznik samego dworca
            station.remove_marker()

            # Usuń obiekty z list
            self.all_stations.pop(selected[0])
            self.all_employees = [e for e in self.all_employees if e.station != station]
            self.all_carriers = [c for c in self.all_carriers if c.station != station]

            # Odśwież widoki
            self.refresh_all()
            self.set_status(f"Usunięto: {station.name}")

    def focus_on_selected_station(self):
        selected = self.stations_listbox.curselection()
        if not selected: return
        station = self.all_stations[selected[0]]
        if station.coordinates:
            self.map_widget.set_position(station.coordinates[0], station.coordinates[1])
            self.map_widget.set_zoom(17)
            self.set_status(f"Wyśrodkowano na: {station.name}")
        else:
            self.set_status(f"Brak współrzędnych dla {station.name}")

    # --- ZAKŁADKA PRACOWNICY ---
    def create_employees_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Pracownicy")

        form = ttk.LabelFrame(tab, text="Formularz Pracownika", padding=10)
        form.pack(fill=X)
        ttk.Label(form, text="Imię i Nazwisko:").grid(row=0, column=0, sticky=W, padx=5, pady=3)
        self.emp_name_entry = ttk.Entry(form)
        self.emp_name_entry.grid(row=0, column=1, sticky=EW, padx=5, pady=3)
        ttk.Label(form, text="Stanowisko:").grid(row=1, column=0, sticky=W, padx=5, pady=3)
        self.emp_pos_entry = ttk.Entry(form)
        self.emp_pos_entry.grid(row=1, column=1, sticky=EW, padx=5, pady=3)
        ttk.Label(form, text="Przypisz do dworca:").grid(row=2, column=0, sticky=W, padx=5, pady=3)
        self.emp_station_combo = ttk.Combobox(form, state="readonly")
        self.emp_station_combo.grid(row=2, column=1, sticky=EW, padx=5, pady=3)
        ttk.Button(form, text="Dodaj Pracownika", command=self.add_employee).grid(row=3, columnspan=2, pady=10)
        form.columnconfigure(1, weight=1)

        list_frame = ttk.LabelFrame(tab, text="Lista Pracowników", padding=10)
        list_frame.pack(fill=BOTH, expand=True, pady=10)
        self.employees_listbox = Listbox(list_frame, font=("Helvetica", 9), relief=SUNKEN, bd=1)
        self.employees_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=LEFT, fill=Y, padx=5)

        ### ZMIANA: Dodano nowy przycisk do pokazywania/ukrywania pracownika na mapie
        ttk.Button(btn_frame, text="Pokaż/Ukryj na Mapie", command=self.toggle_employee_on_map).pack(pady=2)
        ttk.Button(btn_frame, text="Pokaż szczegóły", command=self.show_selected_employee_details).pack(pady=2)
        ttk.Button(btn_frame, text="Usuń Zaznaczonego", command=self.remove_employee).pack(pady=2)

    def add_employee(self):
        name, pos, idx = self.emp_name_entry.get(), self.emp_pos_entry.get(), self.emp_station_combo.current()
        if not all((name, pos, idx != -1)):
            messagebox.showerror("Błąd", "Wszystkie pola są wymagane.")
            return
        station = self.all_stations[idx]

        ### ZMIANA: Znacznik pracownika nie jest już domyślnie umieszczany na mapie.
        employee = Employee(name, pos, station, self)
        # employee.place_marker(self.map_widget) # Usunięto tę linię
        self.all_employees.append(employee)
        station.employees.append(employee)
        self.refresh_all()
        self.set_status(f"Dodano pracownika: {name}")
        self.emp_name_entry.delete(0, END)
        self.emp_pos_entry.delete(0, END)

    ### ZMIANA: Nowa metoda do przełączania widoczności znacznika pracownika
    def toggle_employee_on_map(self):
        selected = self.employees_listbox.curselection()
        if not selected: return
        employee = self.all_employees[selected[0]]

        if employee.marker:
            employee.remove_marker()
            self.set_status(f"Ukryto na mapie: {employee.name}")
        else:
            self._place_entity_offset(employee)

    def show_selected_employee_details(self):
        selected = self.employees_listbox.curselection()
        if not selected: return
        emp_obj = self.all_employees[selected[0]]
        self.show_entity_details(emp_obj)

    def remove_employee(self):
        selected = self.employees_listbox.curselection()
        if not selected: return
        emp = self.all_employees.pop(selected[0])
        emp.remove_marker()  # Usuwa znacznik, jeśli istnieje
        emp.station.employees.remove(emp)
        self.refresh_all()
        self.set_status(f"Usunięto: {emp.name}")

    # --- ZAKŁADKA KLIENCI ---
    def create_clients_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Klienci")

        form = ttk.LabelFrame(tab, text="Formularz Klienta", padding=10)
        form.pack(fill=X)
        ttk.Label(form, text="Nazwa Przewoźnika:").grid(row=0, column=0, sticky=W, padx=5, pady=3)
        self.carrier_name_entry = ttk.Entry(form)
        self.carrier_name_entry.grid(row=0, column=1, sticky=EW, padx=5, pady=3)
        ttk.Label(form, text="Typ taboru:").grid(row=1, column=0, sticky=W, padx=5, pady=3)
        self.carrier_fleet_entry = ttk.Entry(form)
        self.carrier_fleet_entry.grid(row=1, column=1, sticky=EW, padx=5, pady=3)
        ttk.Label(form, text="Przypisz do dworca:").grid(row=2, column=0, sticky=W, padx=5, pady=3)
        self.carrier_station_combo = ttk.Combobox(form, state="readonly")
        self.carrier_station_combo.grid(row=2, column=1, sticky=EW, padx=5, pady=3)
        ttk.Button(form, text="Dodaj Klienta", command=self.add_carrier).grid(row=3, columnspan=2, pady=10)
        form.columnconfigure(1, weight=1)

        list_frame = ttk.LabelFrame(tab, text="Lista Klientów", padding=10)
        list_frame.pack(fill=BOTH, expand=True, pady=10)
        self.carriers_listbox = Listbox(list_frame, font=("Helvetica", 9), relief=SUNKEN, bd=1)
        self.carriers_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=LEFT, fill=Y, padx=5)

        ### ZMIANA: Dodano nowy przycisk do pokazywania/ukrywania klienta na mapie
        ttk.Button(btn_frame, text="Pokaż/Ukryj na Mapie", command=self.toggle_carrier_on_map).pack(pady=2)
        ttk.Button(btn_frame, text="Pokaż szczegóły", command=self.show_selected_carrier_details).pack(pady=2)
        ttk.Button(btn_frame, text="Usuń Zaznaczonego", command=self.remove_carrier).pack(pady=2)

    def add_carrier(self):
        name, fleet, idx = self.carrier_name_entry.get(), self.carrier_fleet_entry.get(), self.carrier_station_combo.current()
        if not all((name, fleet, idx != -1)):
            messagebox.showerror("Błąd", "Wszystkie pola są wymagane.")
            return
        station = self.all_stations[idx]

        ### ZMIANA: Znacznik klienta nie jest już domyślnie umieszczany na mapie.
        carrier = Carrier(name, fleet, station, self)
        # carrier.place_marker(self.map_widget) # Usunięto tę linię
        self.all_carriers.append(carrier)
        station.carriers.append(carrier)
        self.refresh_all()
        self.set_status(f"Dodano przewoźnika: {name}")
        self.carrier_name_entry.delete(0, END)
        self.carrier_fleet_entry.delete(0, END)

    ### ZMIANA: Nowa metoda do przełączania widoczności znacznika klienta
    def toggle_carrier_on_map(self):
        selected = self.carriers_listbox.curselection()
        if not selected: return
        carrier = self.all_carriers[selected[0]]

        if carrier.marker:
            carrier.remove_marker()
            self.set_status(f"Ukryto na mapie: {carrier.name}")
        else:
            self._place_entity_offset(carrier)

    def show_selected_carrier_details(self):
        selected = self.carriers_listbox.curselection()
        if not selected: return
        carrier_obj = self.all_carriers[selected[0]]
        self.show_entity_details(carrier_obj)

    def remove_carrier(self):
        selected = self.carriers_listbox.curselection()
        if not selected: return
        carrier = self.all_carriers.pop(selected[0])
        carrier.remove_marker()  # Usuwa znacznik, jeśli istnieje
        carrier.station.carriers.remove(carrier)
        self.refresh_all()
        self.set_status(f"Usunięto: {carrier.name}")

    # --- ODŚWIEŻANIE INTERFEJSU ---
    def refresh_all(self):
        """Jedna metoda do odświeżania wszystkich list i kontrolek."""
        self.stations_listbox.delete(0, END)
        for s in self.all_stations:
            self.stations_listbox.insert(END, f"{s.name} ({s.address})")

        self.employees_listbox.delete(0, END)
        for e in self.all_employees:
            self.employees_listbox.insert(END, f"{e.name} [{e.station.name}]")

        self.carriers_listbox.delete(0, END)
        for c in self.all_carriers:
            self.carriers_listbox.insert(END, f"{c.name} [{c.station.name}]")

        station_names = [s.name for s in self.all_stations]
        self.emp_station_combo['values'] = station_names
        self.carrier_station_combo['values'] = station_names


if __name__ == "__main__":
    app = App()
    app.mainloop()