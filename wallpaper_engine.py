import os
import sys
import random
import sqlite3
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import win32api
import win32con
import win32gui
from pystray import Icon, Menu, MenuItem
from PIL import Image as PilImage

# Configure customtkinter appearance
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class WallpaperEngine:
    def __init__(self):
        # Database setup
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallpaper_engine.db")
        self.setup_database()
        
        # Initialize variables
        self.wallpapers = []
        self.current_wallpaper_index = 0
        self.loop_enabled = False
        self.shuffle_enabled = False
        self.all_monitors = False
        self.loop_timer = None
        self.loop_interval = 60  # Default 60 seconds
        
        # Load saved settings
        self.load_settings()
        
        # Initialize UI
        self.app = ctk.CTk()
        self.app.title("Wallpaper Engine")
        self.app.geometry("1000x600")
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create system tray icon
        self.setup_system_tray()
        
        # Setup UI components
        self.setup_ui()
        
        # Load wallpapers from database
        self.load_wallpapers_from_db()
        
        # Start the loop if it was enabled
        if self.loop_enabled:
            self.start_wallpaper_loop()
    
    def setup_database(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create wallpapers table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallpapers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE
        )
        ''')
        
        # Create settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            loop_enabled INTEGER DEFAULT 0,
            shuffle_enabled INTEGER DEFAULT 0,
            all_monitors INTEGER DEFAULT 0,
            loop_interval INTEGER DEFAULT 60
        )
        ''')
        
        # Insert default settings if not exists
        cursor.execute("INSERT OR IGNORE INTO settings (id, loop_enabled, shuffle_enabled, all_monitors, loop_interval) VALUES (1, 0, 0, 0, 60)")
        
        conn.commit()
        conn.close()
    
    def load_settings(self):
        """Load settings from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT loop_enabled, shuffle_enabled, all_monitors, loop_interval FROM settings WHERE id = 1")
        result = cursor.fetchone()
        
        if result:
            self.loop_enabled = bool(result[0])
            self.shuffle_enabled = bool(result[1])
            self.all_monitors = bool(result[2])
            self.loop_interval = result[3]
        
        conn.close()
    
    def save_settings(self):
        """Save settings to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE settings 
        SET loop_enabled = ?, shuffle_enabled = ?, all_monitors = ?, loop_interval = ?
        WHERE id = 1
        """, (int(self.loop_enabled), int(self.shuffle_enabled), int(self.all_monitors), self.loop_interval))
        
        conn.commit()
        conn.close()
    
    def setup_ui(self):
        """Setup the main UI components"""
        # Create the tab control
        self.tab_control = ctk.CTkTabview(self.app)
        self.tab_control.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Create the Library tab
        self.library_tab = self.tab_control.add("Library")
        
        # Create the Settings tab
        self.settings_tab = self.tab_control.add("Settings")
        
        # Setup library tab
        self.setup_library_tab()
        
        # Setup settings tab
        self.setup_settings_tab()
    
    def setup_library_tab(self):
        """Setup the library tab UI components"""
        # Top frame for buttons
        top_frame = ctk.CTkFrame(self.library_tab)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        # Add button to load wallpapers
        load_btn = ctk.CTkButton(
            top_frame, 
            text="Load Wallpapers", 
            command=self.load_wallpapers
        )
        load_btn.pack(side="left", padx=10, pady=10)
        
        # Create a scrollable frame for wallpapers
        self.wallpaper_container = ctk.CTkScrollableFrame(self.library_tab)
        self.wallpaper_container.pack(expand=True, fill="both", padx=10, pady=10)
    
    def setup_settings_tab(self):
        """Setup the settings tab UI components"""
        # Create frame for settings
        settings_frame = ctk.CTkFrame(self.settings_tab)
        settings_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Loop settings
        self.loop_var = tk.BooleanVar(value=self.loop_enabled)
        loop_cb = ctk.CTkCheckBox(
            settings_frame, 
            text="Enable Wallpaper Looping", 
            variable=self.loop_var,
            command=self.toggle_loop
        )
        loop_cb.pack(anchor="w", padx=20, pady=10)
        
        # Interval setting
        interval_frame = ctk.CTkFrame(settings_frame)
        interval_frame.pack(fill="x", padx=20, pady=10)
        
        interval_label = ctk.CTkLabel(interval_frame, text="Loop Interval (seconds):")
        interval_label.pack(side="left", padx=5)
        
        self.interval_var = tk.StringVar(value=str(self.loop_interval))
        interval_entry = ctk.CTkEntry(interval_frame, width=80, textvariable=self.interval_var)
        interval_entry.pack(side="left", padx=5)
        
        interval_btn = ctk.CTkButton(
            interval_frame, 
            text="Apply", 
            width=80,
            command=self.update_interval
        )
        interval_btn.pack(side="left", padx=5)
        
        # Shuffle settings
        self.shuffle_var = tk.BooleanVar(value=self.shuffle_enabled)
        shuffle_cb = ctk.CTkCheckBox(
            settings_frame, 
            text="Enable Shuffle Mode", 
            variable=self.shuffle_var,
            command=self.toggle_shuffle
        )
        shuffle_cb.pack(anchor="w", padx=20, pady=10)
        
        # All monitors settings
        self.all_monitors_var = tk.BooleanVar(value=self.all_monitors)
        all_monitors_cb = ctk.CTkCheckBox(
            settings_frame, 
            text="Apply to All Monitors", 
            variable=self.all_monitors_var,
            command=self.toggle_all_monitors
        )
        all_monitors_cb.pack(anchor="w", padx=20, pady=10)
    
    def load_wallpapers(self):
        """Load wallpapers from file system"""
        file_paths = filedialog.askopenfilenames(
            title="Select Wallpaper Files",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if not file_paths:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for path in file_paths:
            try:
                # Insert into database
                cursor.execute("INSERT OR IGNORE INTO wallpapers (path) VALUES (?)", (path,))
                
                # Add to the UI only if it was inserted (not already in DB)
                if cursor.rowcount > 0:
                    self.add_wallpaper_to_ui(path)
            except sqlite3.Error as e:
                print(f"Database error: {e}")
        
        conn.commit()
        conn.close()
    
    def load_wallpapers_from_db(self):
        """Load saved wallpapers from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT path FROM wallpapers")
        wallpapers = cursor.fetchall()
        
        for path, in wallpapers:
            if os.path.exists(path):
                self.add_wallpaper_to_ui(path)
            else:
                # Remove wallpapers that no longer exist
                cursor.execute("DELETE FROM wallpapers WHERE path = ?", (path,))
        
        conn.commit()
        conn.close()
    
    def add_wallpaper_to_ui(self, path):
        """Add a wallpaper to the UI"""
        # Add to wallpapers list
        wallpaper_info = {
            "path": path
        }
        self.wallpapers.append(wallpaper_info)
        
        # Create a frame for this wallpaper
        wallpaper_frame = ctk.CTkFrame(self.wallpaper_container)
        wallpaper_frame.pack(fill="x", padx=10, pady=10)
        
        # Left side for image preview
        preview_frame = ctk.CTkFrame(wallpaper_frame, width=150, height=100)
        preview_frame.pack(side="left", padx=10, pady=10)
        preview_frame.pack_propagate(False)
        
        # Create thumbnail preview
        try:
            img = Image.open(path)
            img.thumbnail((140, 90))
            photo = ImageTk.PhotoImage(img)
            
            thumbnail = ctk.CTkLabel(preview_frame, image=photo, text="")
            thumbnail.image = photo  # Keep a reference
            thumbnail.pack(expand=True, fill="both")
        except Exception as e:
            print(f"Error creating image thumbnail: {e}")
            thumbnail = ctk.CTkLabel(preview_frame, text="Image Preview\nNot Available")
            thumbnail.pack(expand=True, fill="both")
        
        # Right side for information and buttons
        info_frame = ctk.CTkFrame(wallpaper_frame)
        info_frame.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        
        # Wallpaper name (filename)
        name_label = ctk.CTkLabel(info_frame, text=os.path.basename(path), 
                                 anchor="w", font=ctk.CTkFont(weight="bold"))
        name_label.pack(anchor="w", padx=5, pady=5)
        
        # File path
        path_label = ctk.CTkLabel(info_frame, text=path, anchor="w")
        path_label.pack(anchor="w", padx=5, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(info_frame)
        button_frame.pack(anchor="w", padx=5, pady=5)
        
        # Apply button
        apply_btn = ctk.CTkButton(
            button_frame, 
            text="Apply Now", 
            command=lambda p=path: self.set_wallpaper(p)
        )
        apply_btn.pack(side="left", padx=5)
        
        # Remove button
        remove_btn = ctk.CTkButton(
            button_frame, 
            text="Remove", 
            fg_color="red", 
            hover_color="darkred",
            command=lambda p=path, f=wallpaper_frame: self.remove_wallpaper(p, f)
        )
        remove_btn.pack(side="left", padx=5)
    
    def remove_wallpaper(self, path, frame):
        """Remove a wallpaper from the library"""
        # Remove from UI
        frame.destroy()
        
        # Remove from list
        for i, wp in enumerate(self.wallpapers):
            if wp["path"] == path:
                self.wallpapers.pop(i)
                break
        
        # Remove from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wallpapers WHERE path = ?", (path,))
        conn.commit()
        conn.close()
    
    def set_wallpaper(self, image_path):
        """Set an image as wallpaper"""
        try:
            key = win32con.SPIF_UPDATEINIFILE | win32con.SPIF_SENDCHANGE
            if self.all_monitors:
                # Set wallpaper on all monitors (Windows 10 will tile/stretch as per user settings)
                win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, image_path, key)
            else:
                # Set wallpaper only on the primary monitor
                win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, image_path, key)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set wallpaper: {e}")
    
    def toggle_loop(self):
        """Toggle wallpaper looping"""
        self.loop_enabled = self.loop_var.get()
        
        if self.loop_enabled:
            self.start_wallpaper_loop()
        else:
            self.stop_wallpaper_loop()
        
        self.save_settings()
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_enabled = self.shuffle_var.get()
        self.save_settings()
    
    def toggle_all_monitors(self):
        """Toggle applying wallpaper to all monitors"""
        self.all_monitors = self.all_monitors_var.get()
        self.save_settings()
    
    def update_interval(self):
        """Update the loop interval"""
        try:
            interval = int(self.interval_var.get())
            if interval < 5:
                messagebox.showwarning("Warning", "Minimum interval is 5 seconds")
                interval = 5
                self.interval_var.set(str(interval))
            
            self.loop_interval = interval
            self.save_settings()
            
            # Restart loop if it's enabled
            if self.loop_enabled:
                self.stop_wallpaper_loop()
                self.start_wallpaper_loop()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")
            self.interval_var.set(str(self.loop_interval))
    
    def start_wallpaper_loop(self):
        """Start the wallpaper looping"""
        if not self.wallpapers:
            return
        
        if self.loop_timer:
            self.stop_wallpaper_loop()
        
        # Function to change wallpaper
        def change_wallpaper():
            if not self.wallpapers:
                return
            
            if self.shuffle_enabled:
                # Don't select the same wallpaper twice in a row if there are more than one
                if len(self.wallpapers) > 1:
                    current_index = self.current_wallpaper_index
                    while self.current_wallpaper_index == current_index:
                        self.current_wallpaper_index = random.randint(0, len(self.wallpapers) - 1)
                else:
                    self.current_wallpaper_index = 0
            else:
                # Move to the next wallpaper
                self.current_wallpaper_index = (self.current_wallpaper_index + 1) % len(self.wallpapers)
            
            # Apply the wallpaper
            wallpaper = self.wallpapers[self.current_wallpaper_index]
            self.set_wallpaper(wallpaper["path"])
            
            # Schedule the next change
            self.loop_timer = threading.Timer(self.loop_interval, change_wallpaper)
            self.loop_timer.daemon = True
            self.loop_timer.start()
        
        # Start the loop
        change_wallpaper()
    
    def stop_wallpaper_loop(self):
        """Stop the wallpaper looping"""
        if self.loop_timer:
            self.loop_timer.cancel()
            self.loop_timer = None
    
    def setup_system_tray(self):
        """Setup the system tray icon"""
        # Create an icon image
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        
        # Check if the icon exists, if not create a simple one
        if not os.path.exists(icon_path):
            img = PilImage.new('RGB', (64, 64), color=(66, 133, 244))
            img.save(icon_path)
        
        # Load the icon
        icon_image = PilImage.open(icon_path)
        
        # Define the menu
        menu = Menu(
            MenuItem('Show', self.show_window),
            MenuItem('Exit', self.quit_app)
        )
        
        # Create the icon
        self.tray_icon = Icon("wallpaper_engine", icon_image, "Wallpaper Engine", menu)
        
        # Run the icon in a separate thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_window(self):
        """Show the main window"""
        self.app.deiconify()
        self.app.lift()
    
    def hide_window(self):
        """Hide the main window"""
        self.app.withdraw()
    
    def on_close(self):
        """Handle window close event"""
        result = messagebox.askyesno(
            "Hide to System Tray", 
            "The application will be minimized to the system tray.\n\nClick 'Yes' to hide or 'No' to close completely."
        )
        
        if result:
            self.hide_window()
        else:
            self.quit_app()
    
    def quit_app(self):
        """Quit the application"""
        # Stop the loop timer
        if self.loop_timer:
            self.loop_timer.cancel()
        
        # Stop the tray icon
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        
        # Close the app
        self.app.quit()
        sys.exit(0)
    
    def run(self):
        """Run the application"""
        self.app.mainloop()

if __name__ == "__main__":
    app = WallpaperEngine()
    app.run()