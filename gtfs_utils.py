# -*- coding: utf-8 -*-
import pandas as pd
import os
import zipfile
import io
from dotenv import load_dotenv

# Charger les variables d'environnement au cas où le module est utilisé seul
load_dotenv()

class GTFSLoader:
    def __init__(self, gtfs_dir=None):
        # Utilise la variable d'environnement ou le chemin par défaut
        self.gtfs_dir = gtfs_dir or os.getenv("GTFS_STATIC_DIR", "/home/umbrel/Alerts/gtfs_static")
        self.routes = None
        self.stops = None
        self.trips = None
        self.is_loaded = False

    def load(self):
        if not os.path.exists(self.gtfs_dir):
            print(f"Erreur : Le dossier {self.gtfs_dir} n'existe pas.")
            return False

        try:
            # 1. Chercher un fichier .zip dans le dossier
            zip_files = [f for f in os.listdir(self.gtfs_dir) if f.endswith('.zip')]
            
            if zip_files:
                zip_path = os.path.join(self.gtfs_dir, zip_files[0])
                with zipfile.ZipFile(zip_path, 'r') as z:
                    if 'routes.txt' in z.namelist():
                        with z.open('routes.txt') as f:
                            self.routes = pd.read_csv(f, dtype={'route_id': str})
                    
                    if 'stops.txt' in z.namelist():
                        with z.open('stops.txt') as f:
                            self.stops = pd.read_csv(f, dtype={'stop_id': str})
                            
                    if 'trips.txt' in z.namelist():
                        with z.open('trips.txt') as f:
                            self.trips = pd.read_csv(f, dtype={'trip_id': str, 'route_id': str})
                
                self.is_loaded = True
                return True

            # 2. Fallback: Chercher les fichiers .txt individuels
            routes_path = os.path.join(self.gtfs_dir, "routes.txt")
            stops_path = os.path.join(self.gtfs_dir, "stops.txt")
            trips_path = os.path.join(self.gtfs_dir, "trips.txt")

            if os.path.exists(routes_path):
                self.routes = pd.read_csv(routes_path, dtype={'route_id': str})
            
            if os.path.exists(stops_path):
                self.stops = pd.read_csv(stops_path, dtype={'stop_id': str})

            if os.path.exists(trips_path):
                self.trips = pd.read_csv(trips_path, dtype={'trip_id': str, 'route_id': str})

            if self.routes is not None or self.stops is not None:
                self.is_loaded = True
                return True
                
            return False
        except Exception as e:
            print(f"Erreur chargement GTFS: {e}")
            return False

    def validate_route_id(self, route_id):
        if self.routes is None: return True
        return str(route_id) in self.routes['route_id'].values

    def validate_stop_id(self, stop_id):
        if self.stops is None: return True
        return str(stop_id) in self.stops['stop_id'].values

    def validate_trip_id(self, trip_id):
        if self.trips is None: return True
        return str(trip_id) in self.trips['trip_id'].values
