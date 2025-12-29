import ctypes
from ctypes import wintypes
import time

# Estruturas necessárias da API do Windows
user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

def get_window_rect(title_keyword):
    """
    Busca uma janela que contenha 'title_keyword' no título e retorna suas coordenadas.
    
    Returns:
        tuple: (x, y, w, h) ou None se não encontrar.
    """
    found_hwnd = None
    
    def enum_windows_proc(hwnd, lParam):
        nonlocal found_hwnd
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        # Verifica se é visível
        if user32.IsWindowVisible(hwnd) and length > 0:
            if title_keyword.lower() in title.lower():
                found_hwnd = hwnd
                return False # Para a enumeração
        return True

    ENUM_WINDOWS_FUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)
    user32.EnumWindows(ENUM_WINDOWS_FUNC(enum_windows_proc), 0)

    if found_hwnd:
        # Tenta lidar com DPI Awareness para coordenadas corretas
        try:
            shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_AWARE
        except Exception:
            pass # Pode falhar em windows antigos
            
        rect = RECT()
        user32.GetWindowRect(found_hwnd, ctypes.byref(rect))
        
        x = rect.left
        y = rect.top
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        
        # Correção básica para bordas do Windows (opcional, mas ajuda a pegar só o conteúdo)
        # Borda padrão ~8px, Título ~30px
        # x += 8
        # y += 30
        # w -= 16
        # h -= 38
        
        if w > 0 and h > 0:
            return (x, y, w, h)
            
    return None
