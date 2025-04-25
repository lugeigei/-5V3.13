import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import logging
import cv2
import time
import numpy as np
from main import FaceAccessSystem
from hardware import OV5647Controller
from face_detector import FaceDetector
from face_recognitiona import FaceRecognizer

class ControlPanel:
    def __init__(self, master):
        self.master = master
        master.title("zhineng menjin xitong")
        master.geometry("800x600")
        
        self.is_running = True
        
        self.system_running = threading.Event()
        self.register_running = False
        self.register_complete = tk.BooleanVar(value=False)
        
        self.system = FaceAccessSystem()
        self.system.disable_native_window = True
        
        self.create_widgets()
        
        self.preview_thread = threading.Thread(target=self.update_preview)
        self.preview_thread.daemon = True
        self.preview_thread.start()
        
        #self.system.log_callback = self.add_event_log
        
        self.registration_preview_label = ttk.Label(self.master)
        self.registration_preview_label.pack_forget()
        
        master.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def create_widgets(self):
        status_frame = ttk.Frame(self.master)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(
            status_frame,
            text="xitongzhuangtai: daiji",
            font=('helvetica',12))
        self.status_label.pack(side=tk.LEFT)
        

        
        self.preview_label = ttk.Label(self.master)
        #self.preview_label.pack(pady=10)
        self.preview_label.pack(pady=10, fill=tk.BOTH,
                                expand=True, anchor=tk.CENTER)
        
        control_frame = ttk.Frame(self.master)
        control_frame.pack(pady=10)
        
        self.start_btn = ttk.Button(
            control_frame,
            text="qidong xitong",
            command=self.toggle_system)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="shoudong zhuce",
            command=self.show_register_dialog
        ).pack(side=tk.LEFT, padx=5)
        
        
    def toggle_system(self):
        if not self.system_running.is_set():
            self.system_running.set()
            self.start_btn.config(text="tingzhi xitong")
            self.status_label.config(text="xitong zhuangtai: yunxingzhong")
            self.system_thread = threading.Thread(target=self.start_system)
            self.system_thread.start()
        else:
            self.system.shutdown()

    def start_system(self):
        self.system.running = True
        try:
            self.system.run_without_window()
        except Exception as e:
            logging.error(f"xitong yunxing yichang: {str(e)}")
    
    
    def shutdown_system(self):
        try:
            self.is_running = False
            self.system.running = False
            self.system_running.clear()
            if hasattr(self, 'system_thread') and self.system_thread.is_alive():
                self.system_thread.join(timeout=2)
            
            self.system.hardware.cleanup()
            
            for widget in self.master.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
            self.master.after(0, lambda: (
                self.start_btn.config(text="qidong xitong"),
                self.status_label.config(text="xitong zhuangtai: yi tingzhi")))
        except Exception as e:
            logging.error(f"guanbi xingyichang:{str(e)}")
    
    
    def update_preview(self):
        try:
            while self.is_running:
                default_img = np.zeros((480, 640, 3), dtype=np.uint8)
                img = Image.fromarray(default_img)
                imgtk = ImageTk.PhotoImage(image=img)
                
                if self.is_running and self.system.running and hasattr(self.system, 'frame_buffer'):
                    if len(self.system.frame_buffer) > 0:
                        frame = self.system.frame_buffer[-1]
                        #img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        #display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        
#                         label_width = self.preview_label.winfo_width()
#                         label_height = self.preview_label.winfo_height()
#                         if label_width <= 1 or label_height <= 1:
#                             label_width, label_height = 640, 480
                        
                        resized_frame = cv2.resize(frame, (640, 480))
                        resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                        
                        img = Image.fromarray(resized_frame)
                        imgtk = ImageTk.PhotoImage(image=img)
                    if self.master.winfo_exists():
                        self.preview_label.config(image=imgtk)
                        setattr(self.preview_label, 'image', imgtk)
                        self.master.update_idletasks()
                time.sleep(0.1)
        except Exception as e:
            logging.error(f"liulan chuangkou yichang: {str(e)}")
            
                
    def show_register_dialog(self):
        def start_register():
            try:
                self._prepare_registration()
                user_id = self._get_user_id_dialog()
                if user_id:
                    self._start_face_capture(user_id)
            except Exception as e:
                messagebox.showerror("zhuce cuowu",str(e))
            finally:
                self._cleanup_registration()
        self.master.after(0, start_register)
        
    def _prepare_registration(self):
        self.system.running = False
        self.master.after(0, lambda: (
            self.preview_label.pack_forget(),
            self.registration_preview_label.pack(pady=10, fill=tk.BOTH, expand=True)
            #self.registration_preview_label.pack(pady=10)
        ))
        self.register_running = True
        self.registration_preview_label.update_idletasks()
        threading.Thread(
            target=self.update_register_preview,
            args=(self.system.hardware, FaceDetector()),
            daemon=True
        ).start()
                
    def _get_user_id_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("yonghu zhuce")
        dialog.transient(self.master)
        dialog.grab_set()
        
        entry = ttk.Entry(dialog, width=20)
        entry.pack(padx=20, pady=10)
        entry.focus_force()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5)
        
        user_id = None
        
        def on_confirm():
            nonlocal user_id
            user_id = entry.get().strip()
            if not user_id:
                messagebox.showwarning("shuru cuowu","yonghu id buneng weikong")
                return
            dialog.destroy()
        
        ttk.Button(btn_frame, text="que ren",command=on_confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="qu xiao",command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        
        dialog.bind("<Return>", lambda e: on_confirm())
        
        self._center_window(dialog)
        dialog.wait_window()
        return user_id
    
    def _center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')
    
    def update_register_preview(self, hardware, detector):
        try:
            while self.is_running and self.register_running:
                frame = hardware.capture_frame()
                if frame is not None and self.is_running:
#                     label_width = self.registration_preview_label.winfo_width()
#                     label_height = self.registration_preview_label.winfo_height()
#                     if label_width <= 1 or label_height <= 1:
#                         label_width, label_height = 640, 480
#                     resized_frame = cv2.resize(frame, (label_width, label_height))
#                     resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
#                     img = Image.fromarray(resized_frame)
#                     imgtk = ImageTk.PhotoImage(image=img)
                    
                    display_frame = frame.copy()
                    faces = detector.detect_faces(display_frame, return_coords=True)
                    if faces:
                        x1, y1, x2, y2 = faces[0]
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0,255,0), 2)
                        cv2.putText(display_frame, "Ready to Register", (x1, y1-10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
                    img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(cv2.resize(img, (640, 480)))
                    imgtk = ImageTk.PhotoImage(image=img)
                    
                    if self.master.winfo_exists():
                        self.master.after(0, lambda:[
                            self.registration_preview_label.configure(image=imgtk),
                            setattr(self.registration_preview_label, 'image', imgtk)
                        ])
                time.sleep(0.1)
        except Exception as e:
            logging.error(f"zhuce yulan gengxin shibai:{str(e)}")
    
    def _start_face_capture(self, user_id):
        self.master.bind("<space>", lambda e: self._capture_face(user_id))
        self.register_complete.set(False)
        self.master.wait_variable(self.register_complete)
        self.master.unbind("<space>")
    
    def _capture_face(self, user_id):
        try:
            hardware = self.system.hardware
            detector = FaceDetector()
            recognizer = FaceRecognizer()
            
            frame = hardware.capture_frame()
            faces = detector.detect_faces(frame, return_coords=True)
            
            if faces:
                x1, y1, x2, y2 = faces[0]
                face_roi = frame[y1:y2, x1:x2]
                
                if recognizer.register(user_id, face_roi):
                    messagebox.showinfo("zhuce chenggong",f"yonghu {user_id} zhuce wancheng"
                                        ,parent=self.master)
                else:
                    messagebox.showerror("zhuce shibai","cuowu!"
                                         ,parent=self.master)
            else:
                messagebox.showwarning("jianggao","weijian cedaorenlian"
                                       ,parent=self.master)
        except Exception as e:
            messagebox.showerror("zhuce shibai",f"cuowu: {str(e)}"
                                 ,parent=self.master)          
        finally:
            self.register_complete.set(True)
            self.register_running = False
            for widget in self.master.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()

    
    def _cleanup_registration(self):
        self.master.after(0, lambda: (
            self.registration_preview_label.pack_forget(),
            self.preview_label.pack(pady=10, fill=tk.BOTH, expand=True)
            #self.preview_label.pack(pady=10)
        ))
        self.system.running = True
    
    
    def _on_space_pressed(self, event):
        self._capture_face()
        self.register_complete.set(True)
        
        
    def on_close(self):
        self.is_running = False
        self.shutdown_system()
        self.master.destroy()  
        
if __name__ == "__main__":
    root = tk.Tk()
    app = ControlPanel(root)
    root.mainloop()
    