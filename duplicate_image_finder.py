import os
import hashlib
from PIL import Image, ImageTk
import imagehash
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import shutil
import mimetypes
import threading
import time
from datetime import datetime
import json
from pathlib import Path

class DuplicateImageFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate Image Finder")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # Ana frame
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Başlık
        title_label = ttk.Label(self.main_frame, text="Duplicate Image Finder", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Sol Panel (Dizin seçimi ve ayarlar)
        left_panel = ttk.Frame(self.main_frame)
        left_panel.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Dizin seçme butonu
        self.select_dir_btn = ttk.Button(left_panel, text="Dizin Seç", command=self.select_directory, style="Accent.TButton")
        self.select_dir_btn.grid(row=0, column=0, pady=10, sticky=tk.W)
        
        # Seçilen dizin etiketi
        self.dir_label = ttk.Label(left_panel, text="Dizin seçilmedi", font=("Helvetica", 10))
        self.dir_label.grid(row=1, column=0, pady=10, sticky=tk.W)
        
        # Karşılaştırma seçenekleri
        ttk.Label(left_panel, text="Karşılaştırma Seçenekleri:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, pady=(20, 5), sticky=tk.W)
        
        self.compare_var = tk.StringVar(value="both")
        ttk.Radiobutton(left_panel, text="Sadece Resimler", variable=self.compare_var, value="images").grid(row=3, column=0, sticky=tk.W)
        ttk.Radiobutton(left_panel, text="Sadece Videolar", variable=self.compare_var, value="videos").grid(row=4, column=0, sticky=tk.W)
        ttk.Radiobutton(left_panel, text="Hepsi", variable=self.compare_var, value="both").grid(row=5, column=0, sticky=tk.W)
        
        # Filtreleme seçenekleri
        ttk.Label(left_panel, text="Filtreleme:", font=("Helvetica", 10, "bold")).grid(row=6, column=0, pady=(20, 5), sticky=tk.W)
        
        # İstatistikler
        self.stats_frame = ttk.LabelFrame(left_panel, text="İstatistikler", padding="10")
        self.stats_frame.grid(row=7, column=0, pady=20, sticky=(tk.W, tk.E))
        
        self.total_files_label = ttk.Label(self.stats_frame, text="Toplam Dosya: 0")
        self.total_files_label.grid(row=0, column=0, sticky=tk.W)
        
        self.duplicate_files_label = ttk.Label(self.stats_frame, text="Tekrar Eden: 0")
        self.duplicate_files_label.grid(row=1, column=0, sticky=tk.W)
        
        self.saved_space_label = ttk.Label(self.stats_frame, text="Kazanılan Alan: 0 KB")
        self.saved_space_label.grid(row=2, column=0, sticky=tk.W)
        
        # Orta Panel (Dosya listesi)
        middle_panel = ttk.Frame(self.main_frame)
        middle_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(middle_panel, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Progress label
        self.progress_label = ttk.Label(middle_panel, text="", font=("Helvetica", 10))
        self.progress_label.grid(row=1, column=0, pady=(0, 10))
        
        # Sonuçlar için treeview
        self.tree = ttk.Treeview(middle_panel, columns=("Path", "Size", "Type", "Date"), show="headings", height=15)
        self.tree.heading("Path", text="Dosya Yolu")
        self.tree.heading("Size", text="Boyut")
        self.tree.heading("Type", text="Tür")
        self.tree.heading("Date", text="Tarih")
        self.tree.column("Path", width=300)
        self.tree.column("Size", width=100)
        self.tree.column("Type", width=100)
        self.tree.column("Date", width=150)
        self.tree.grid(row=2, column=0, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(middle_panel, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Buton frame
        button_frame = ttk.Frame(middle_panel)
        button_frame.grid(row=3, column=0, pady=10)
        
        # Silme butonu
        self.delete_btn = ttk.Button(button_frame, text="Seçili Dosyaları Sil", command=self.delete_selected, style="Accent.TButton")
        self.delete_btn.grid(row=0, column=0, padx=5)
        
        # Yenileme butonu
        self.refresh_btn = ttk.Button(button_frame, text="Yenile", command=self.refresh_scan, style="Accent.TButton")
        self.refresh_btn.grid(row=0, column=1, padx=5)
        
        # Yedekleme butonu
        self.backup_btn = ttk.Button(button_frame, text="Yedekle", command=self.backup_selected, style="Accent.TButton")
        self.backup_btn.grid(row=0, column=2, padx=5)
        
        # İptal butonu
        self.cancel_btn = ttk.Button(button_frame, text="İptal", command=self.cancel_scan, style="Accent.TButton")
        self.cancel_btn.grid(row=0, column=3, padx=5)
        self.cancel_btn.config(state="disabled")
        
        # Sağ Panel (Önizleme)
        right_panel = ttk.LabelFrame(self.main_frame, text="Önizleme", padding="10")
        right_panel.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        self.preview_label = ttk.Label(right_panel)
        self.preview_label.grid(row=0, column=0, pady=10)
        
        self.preview_info = ttk.Label(right_panel, text="", wraplength=200)
        self.preview_info.grid(row=1, column=0, pady=10)
        
        # Grid yapılandırması
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        middle_panel.columnconfigure(0, weight=1)
        middle_panel.rowconfigure(2, weight=1)
        
        # Stil yapılandırması
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        
        # Event bindings
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        self.duplicate_groups = []
        self.scanning = False
        self.backup_dir = None
        
    def select_directory(self):
        if self.scanning:
            messagebox.showwarning("Uyarı", "Tarama işlemi devam ediyor!")
            return
            
        directory = filedialog.askdirectory()
        if directory:
            self.dir_label.config(text=directory)
            self.start_scan(directory)
    
    def start_scan(self, directory):
        self.scanning = True
        self.progress_var.set(0)
        self.progress_label.config(text="Tarama başlatılıyor...")
        self.select_dir_btn.config(state="disabled")
        self.delete_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")
        self.backup_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        
        # Tarama işlemini ayrı bir thread'de başlat
        thread = threading.Thread(target=self.find_duplicates, args=(directory,))
        thread.daemon = True
        thread.start()
    
    def find_duplicates(self, directory):
        try:
            # Treeview'ı temizle
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Resim hash'lerini saklamak için sözlük
            hash_dict = defaultdict(list)
            
            # Desteklenen medya formatları
            media_extensions = {
                # Resim formatları
                '.jpg': 'Resim', '.jpeg': 'Resim', '.png': 'Resim', '.bmp': 'Resim', 
                '.gif': 'Resim', '.tiff': 'Resim', '.webp': 'Resim', '.ico': 'Resim',
                # Video formatları
                '.mp4': 'Video', '.avi': 'Video', '.mov': 'Video', '.wmv': 'Video',
                '.flv': 'Video', '.mkv': 'Video', '.webm': 'Video'
            }
            
            # Karşılaştırma seçeneklerine göre formatları filtrele
            compare_type = self.compare_var.get()
            if compare_type == "images":
                media_extensions = {k: v for k, v in media_extensions.items() if v == "Resim"}
            elif compare_type == "videos":
                media_extensions = {k: v for k, v in media_extensions.items() if v == "Video"}
            
            # Toplam dosya sayısını hesapla
            total_files = sum(1 for root, _, files in os.walk(directory) 
                            for f in files if f.lower().endswith(tuple(media_extensions.keys())))
            
            if total_files == 0:
                self.update_progress(100, "Tarama tamamlandı - Dosya bulunamadı")
                return
                
            processed_files = 0
            total_size = 0
            
            # Dizindeki tüm dosyaları tara
            for root, _, files in os.walk(directory):
                for filename in files:
                    if self.scanning == False:
                        return
                        
                    filepath = os.path.join(root, filename)
                    ext = os.path.splitext(filename)[1].lower()
                    
                    if ext in media_extensions:
                        try:
                            file_size = os.path.getsize(filepath)
                            
                            if media_extensions[ext] == 'Resim':
                                # Resmi aç ve hash'ini hesapla
                                with Image.open(filepath) as img:
                                    phash = str(imagehash.average_hash(img))
                                    hash_dict[phash].append((filepath, media_extensions[ext], file_size))
                            else:
                                # Video dosyaları için dosya boyutunu ve adını kullan
                                hash_dict[f"{filename}_{file_size}"].append((filepath, media_extensions[ext], file_size))
                            
                            total_size += file_size
                            
                        except Exception as e:
                            print(f"Hata: {filepath} - {str(e)}")
                            
                        processed_files += 1
                        progress = (processed_files / total_files) * 100
                        self.update_progress(progress, f"Taranıyor: {processed_files}/{total_files} dosya")
            
            # Tekrar eden dosyaları bul
            self.duplicate_groups = []
            duplicate_count = 0
            saved_space = 0
            
            for hash_value, filepaths in hash_dict.items():
                if len(filepaths) > 1:
                    self.duplicate_groups.append(filepaths)
                    # İlk dosyayı orijinal olarak kabul et, diğerlerini tekrar eden olarak işaretle
                    for filepath, file_type, file_size in filepaths[1:]:
                        size_kb = file_size / 1024
                        date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
                        self.tree.insert("", "end", values=(filepath, f"{size_kb:.2f} KB", file_type, date))
                        duplicate_count += 1
                        saved_space += file_size
            
            # İstatistikleri güncelle
            self.total_files_label.config(text=f"Toplam Dosya: {total_files}")
            self.duplicate_files_label.config(text=f"Tekrar Eden: {duplicate_count}")
            self.saved_space_label.config(text=f"Kazanılan Alan: {saved_space/1024:.2f} KB")
            
            self.update_progress(100, "Tarama tamamlandı")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Tarama sırasında bir hata oluştu: {str(e)}")
        finally:
            self.scanning = False
            self.select_dir_btn.config(state="normal")
            self.delete_btn.config(state="normal")
            self.refresh_btn.config(state="normal")
            self.backup_btn.config(state="normal")
            self.cancel_btn.config(state="disabled")
    
    def update_progress(self, value, text):
        self.progress_var.set(value)
        self.progress_label.config(text=text)
        self.root.update_idletasks()
    
    def on_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            filepath = self.tree.item(selected_items[0])["values"][0]
            file_type = self.tree.item(selected_items[0])["values"][2]
            
            try:
                if file_type == "Resim":
                    # Resim önizlemesi
                    image = Image.open(filepath)
                    # Önizleme boyutunu ayarla
                    max_size = (200, 200)
                    image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.preview_label.config(image=photo)
                    self.preview_label.image = photo
                else:
                    # Video için önizleme yok
                    self.preview_label.config(image="")
                    self.preview_label.image = None
                
                # Dosya bilgilerini göster
                size = os.path.getsize(filepath) / 1024
                date = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
                self.preview_info.config(text=f"Boyut: {size:.2f} KB\nTarih: {date}")
                
            except Exception as e:
                self.preview_label.config(image="")
                self.preview_label.image = None
                self.preview_info.config(text=f"Önizleme yüklenemedi: {str(e)}")
    
    def delete_selected(self):
        if self.scanning:
            messagebox.showwarning("Uyarı", "Tarama işlemi devam ediyor!")
            return
            
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silinecek dosyaları seçin!")
            return
            
        if messagebox.askyesno("Onay", "Seçili dosyaları silmek istediğinizden emin misiniz?"):
            for item in selected_items:
                filepath = self.tree.item(item)["values"][0]
                try:
                    os.remove(filepath)
                    self.tree.delete(item)
                except Exception as e:
                    messagebox.showerror("Hata", f"Dosya silinirken hata oluştu: {str(e)}")
            
            messagebox.showinfo("Başarılı", "Seçili dosyalar başarıyla silindi!")
            self.refresh_scan()
    
    def backup_selected(self):
        if self.scanning:
            messagebox.showwarning("Uyarı", "Tarama işlemi devam ediyor!")
            return
            
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen yedeklenecek dosyaları seçin!")
            return
            
        if not self.backup_dir:
            self.backup_dir = filedialog.askdirectory(title="Yedekleme Dizini Seç")
            if not self.backup_dir:
                return
        
        try:
            for item in selected_items:
                filepath = self.tree.item(item)["values"][0]
                filename = os.path.basename(filepath)
                backup_path = os.path.join(self.backup_dir, filename)
                
                # Aynı isimde dosya varsa numara ekle
                counter = 1
                while os.path.exists(backup_path):
                    name, ext = os.path.splitext(filename)
                    backup_path = os.path.join(self.backup_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                shutil.copy2(filepath, backup_path)
            
            messagebox.showinfo("Başarılı", "Seçili dosyalar başarıyla yedeklendi!")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Yedekleme sırasında bir hata oluştu: {str(e)}")
    
    def refresh_scan(self):
        if self.scanning:
            messagebox.showwarning("Uyarı", "Tarama işlemi devam ediyor!")
            return
            
        current_dir = self.dir_label.cget("text")
        if current_dir != "Dizin seçilmedi":
            self.start_scan(current_dir)
        else:
            messagebox.showwarning("Uyarı", "Lütfen önce bir dizin seçin!")
    
    def cancel_scan(self):
        if self.scanning:
            self.scanning = False
            self.progress_label.config(text="Tarama iptal edildi")
            self.update_progress(0, "Tarama iptal edildi")

if __name__ == "__main__":
    root = tk.Tk()
    app = DuplicateImageFinder(root)
    root.mainloop() 