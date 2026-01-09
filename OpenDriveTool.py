import tkinter as tk
from tkinter import messagebox
import requests
import subprocess
import shutil
import os
import sys
import threading
import math
import datetime
import re

# --- TRY IMPORTING MAP LIBRARY ---
try:
    import tkintermapview
except ImportError:
    pass

# --- HELPER: FIND NETCONVERT ---
def get_netconvert_path():
    """Checks for netconvert in the current directory first, then system PATH."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Check inside 'sumo_bin' folder first
    subfolder_exe = os.path.join(base_path, "sumo_bin", "netconvert.exe")
    if os.path.exists(subfolder_exe):
        return subfolder_exe

    # Check same folder
    local_exe = os.path.join(base_path, "netconvert.exe")
    if os.path.exists(local_exe):
        return local_exe
        
    # Check installed system path
    return shutil.which("netconvert")

# --- BACKEND LOGIC ---
def run_conversion(south, west, north, east, output_folder, file_prefix, status_callback):
    
    # 1. SETUP PATHS
    osm_file = os.path.join(output_folder, f"{file_prefix}.osm")
    xodr_file = os.path.join(output_folder, f"{file_prefix}.xodr")
    
    # 2. DOWNLOAD (Robust Multi-Server)
    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    query = f"""
    [out:xml][timeout:300][maxsize:200000000];
    (
      way({south},{west},{north},{east});
    );
    (._;>;);
    out meta;
    """

    status_callback(f"Downloading: {file_prefix}...")
    download_success = False
    
    for url in servers:
        try:
            print(f"Trying server: {url}")
            response = requests.post(url, data=query, timeout=310) 
            response.raise_for_status()
            
            if "Gateway Time-out" in response.text or "Error" in response.text[:50]:
                raise Exception("Server returned error text")
                
            with open(osm_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            download_success = True
            break
        except Exception as e:
            print(f"Server {url} failed: {e}")
            continue

    if not download_success:
        status_callback("Error: All map servers timed out.")
        return

    # 3. CONVERT (SUMO)
    status_callback("Converting and Cropping...")
    
    netconvert_bin = get_netconvert_path()
    if not netconvert_bin:
        status_callback("Error: 'netconvert.exe' not found.")
        return

    geo_boundary = f"{west},{south},{east},{north}"
    
    command = [
        netconvert_bin,
        "--osm-files", osm_file,
        "--opendrive-output", xodr_file,
        "--keep-edges.in-geo-boundary", geo_boundary,
        "--keep-edges.by-vclass", "passenger",
        "--geometry.remove", 
        "--no-warnings"
    ]

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        result = subprocess.run(command, capture_output=True, text=True, startupinfo=startupinfo)
        
        if result.returncode == 0:
            if os.path.exists(xodr_file):
                size_kb = os.path.getsize(xodr_file) / 1024
                status_callback(f"SUCCESS! Saved {file_prefix}.xodr ({size_kb:.1f} KB)")
            else:
                status_callback("Error: Output file empty.")
        else:
            status_callback(f"SUMO Failed. See console.")
            print(result.stderr)
    except Exception as e:
        status_callback(f"Execution Error: {e}")

# --- REVERSE GEOCODING ---
def get_location_name(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {'lat': lat, 'lon': lon, 'format': 'json', 'zoom': 10}
    headers = {'User-Agent': 'OpenDriveGenerator/1.0 (python-requests)'}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            address = data.get('address', {})
            name = address.get('city') or address.get('town') or address.get('village') or address.get('county') or "Unknown_Location"
            return name
    except Exception:
        pass
    return "Unknown_Location"

# --- CUSTOM SEARCH ---
def custom_nominatim_search(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': query, 'format': 'json', 'limit': 1, 'addressdetails': 1}
    headers = {'User-Agent': 'OpenDriveGenerator/1.0 (python-requests)'}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon']), data[0]['display_name']
        return None
    except Exception as e:
        print(f"Search failed: {e}")
        return None

# --- GUI CLASS ---
class MapSelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenDRIVE Map Generator")
        self.root.geometry("1000x800")

        # --- SETUP OUTPUT FOLDER ---
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        self.output_folder = os.path.join(desktop, "OpenDriveMaps")
        if not os.path.exists(self.output_folder):
            try:
                os.makedirs(self.output_folder)
            except OSError:
                self.output_folder = os.getcwd()

        # --- TOP BAR ---
        self.search_frame = tk.Frame(root, height=50, bg="#dddddd")
        self.search_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(self.search_frame, text="Search:", bg="#dddddd").pack(side=tk.LEFT, padx=10)
        self.entry_search = tk.Entry(self.search_frame, width=30)
        self.entry_search.pack(side=tk.LEFT, padx=5)
        self.entry_search.bind("<Return>", self.perform_search)
        
        self.btn_search = tk.Button(self.search_frame, text="Go", command=self.perform_search)
        self.btn_search.pack(side=tk.LEFT, padx=5)
        
        self.lbl_status = tk.Label(self.search_frame, text="", bg="#dddddd", fg="blue")
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        tk.Label(self.search_frame, text="Right-click & Drag to select", fg="gray", bg="#dddddd").pack(side=tk.RIGHT, padx=10)

        # --- MAIN MAP ---
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        cache_path = os.path.join(os.path.expanduser("~"), "map_cache.db")
        self.map_widget = tkintermapview.TkinterMapView(
            self.top_frame, 
            corner_radius=0,
            use_database_only=False,
            database_path=cache_path
        )
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_zoom(2)

        # --- BOTTOM BAR ---
        self.bottom_frame = tk.Frame(root, height=60, bg="#f0f0f0")
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.info_label = tk.Label(self.bottom_frame, text=f"Saving to: {self.output_folder}", font=("Arial", 9), bg="#f0f0f0", fg="gray")
        self.info_label.pack(side=tk.LEFT, padx=10, pady=10)

        self.btn_download = tk.Button(self.bottom_frame, text="Download Selection", state="disabled", command=self.start_download, bg="#cccccc", font=("Arial", 10, "bold"))
        self.btn_download.pack(side=tk.RIGHT, padx=20, pady=10)

        # --- VARIABLES ---
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.selection_polygon = None
        self.selection_coords = None 

        # --- BINDINGS ---
        self.map_widget.canvas.bind("<Button-3>", self.on_mouse_down)
        self.map_widget.canvas.bind("<B3-Motion>", self.on_mouse_drag)
        self.map_widget.canvas.bind("<ButtonRelease-3>", self.on_mouse_up)

    def perform_search(self, event=None):
        query = self.entry_search.get()
        if not query: return
        self.lbl_status.config(text="Searching...", fg="blue")
        
        def _search():
            result = custom_nominatim_search(query)
            if result:
                lat, lon, name = result
                
                # --- FIX FOR SEARCH BUG ---
                def move_camera():
                    # Set position first
                    self.map_widget.set_position(lat, lon)
                    self.map_widget.set_zoom(15)
                    # Force a second update 100ms later to handle rendering lag
                    self.root.after(100, lambda: self.map_widget.set_position(lat, lon))
                    self.lbl_status.config(text=f"Found: {name[:30]}...", fg="green")

                # Run on main thread
                self.root.after(0, move_camera)
            else:
                self.root.after(0, lambda: self.lbl_status.config(text="Location not found.", fg="red"))
        
        threading.Thread(target=_search, daemon=True).start()

    def on_mouse_down(self, event):
        if self.rect_id:
            self.map_widget.canvas.delete(self.rect_id)
            self.rect_id = None
        if self.selection_polygon:
            self.selection_polygon.delete()
            self.selection_polygon = None
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.map_widget.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

    def on_mouse_drag(self, event):
        if self.rect_id:
            self.map_widget.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
            start_coords = self.map_widget.convert_canvas_coords_to_decimal_coords(self.start_x, self.start_y)
            end_coords = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
            if start_coords and end_coords:
                lat1, lon1 = start_coords
                lat2, lon2 = end_coords
                south, north = min(lat1, lat2), max(lat1, lat2)
                west, east = min(lon1, lon2), max(lon1, lon2)
                h_km = (north - south) * 111
                avg_lat_rad = math.radians((north + south) / 2)
                w_km = (east - west) * 111 * math.cos(avg_lat_rad)
                if w_km > 10 or h_km > 10:
                    self.info_label.config(text=f"Size: {w_km:.1f}x{h_km:.1f} km (TOO BIG)", fg="red")
                else:
                    self.info_label.config(text=f"Size: {w_km:.2f}x{h_km:.2f} km", fg="blue")

    def on_mouse_up(self, event):
        start_coords = self.map_widget.convert_canvas_coords_to_decimal_coords(self.start_x, self.start_y)
        end_coords = self.map_widget.convert_canvas_coords_to_decimal_coords(event.x, event.y)
        if self.rect_id:
            self.map_widget.canvas.delete(self.rect_id)
            self.rect_id = None
        if not start_coords or not end_coords: return
        lat1, lon1 = start_coords
        lat2, lon2 = end_coords
        south, north = min(lat1, lat2), max(lat1, lat2)
        west, east = min(lon1, lon2), max(lon1, lon2)
        self.selection_coords = (south, west, north, east)
        h_km = (north - south) * 111
        avg_lat_rad = math.radians((north + south) / 2)
        w_km = (east - west) * 111 * math.cos(avg_lat_rad)
        dist_px = math.hypot(event.x - self.start_x, event.y - self.start_y)
        if dist_px < 10:
            self.info_label.config(text=f"Saved to: {self.output_folder}", fg="gray")
            self.btn_download.config(state="disabled", bg="#cccccc")
            return
        label_txt = f"Selection: {w_km:.2f} km x {h_km:.2f} km"
        if w_km <= 10.0 and h_km <= 10.0:
            self.selection_polygon = self.map_widget.set_polygon([(north, west), (north, east), (south, east), (south, west)], fill_color=None, outline_color="red", border_width=3, name="selection")
        if w_km > 10.0 or h_km > 10.0:
            self.info_label.config(text=label_txt + " (LIMIT 10KM)", fg="red")
            self.btn_download.config(state="disabled", bg="#cccccc")
        else:
            self.info_label.config(text=label_txt + " (Ready)", fg="green")
            self.btn_download.config(state="normal", bg="#4CAF50")

    def start_download(self):
        if not self.selection_coords: return
        self.btn_download.config(text="Processing...", state="disabled", bg="orange")
        t = threading.Thread(target=self.prepare_and_run)
        t.start()

    def prepare_and_run(self):
        search_text = self.entry_search.get().strip()
        if search_text:
            base_name = search_text
        else:
            s, w, n, e = self.selection_coords
            center_lat = (s + n) / 2
            center_lon = (w + e) / 2
            self.root.after(0, lambda: self.info_label.config(text="Identifying location name..."))
            base_name = get_location_name(center_lat, center_lon)
        
        base_name = re.sub(r'[<>:"/\\|?*]', '', base_name).replace(" ", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_prefix = f"{base_name}_{timestamp}"
        self.run_process(file_prefix)

    def run_process(self, file_prefix):
        s, w, n, e = self.selection_coords
        def update_status(msg):
            self.root.after(0, lambda: self.info_label.config(text=msg))
            if "SUCCESS" in msg:
                self.root.after(0, lambda: self.btn_download.config(text="Done! Select New", state="normal", bg="#4CAF50"))
                self.root.after(0, lambda: messagebox.showinfo("Conversion Complete", f"Saved:\n{file_prefix}.xodr"))
            elif "Error" in msg:
                self.root.after(0, lambda: self.btn_download.config(text="Retry", state="normal", bg="#f44336"))
        run_conversion(s, w, n, e, self.output_folder, file_prefix, update_status)

if __name__ == "__main__":
    root = tk.Tk()
    app = MapSelectorApp(root)
    root.mainloop()