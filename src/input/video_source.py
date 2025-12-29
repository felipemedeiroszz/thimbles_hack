import mss
import cv2
import time
from abc import ABC, abstractmethod
import numpy as np

class VideoSource(ABC):
    """
    Classe base abstrata para fontes de vídeo.
    Define a interface que todas as fontes de vídeo devem implementar.
    """
    
    @abstractmethod
    def get_frame(self):
        """
        Captura e retorna o próximo frame do vídeo.
        
        Returns:
            frame (numpy.ndarray): O frame capturado em formato BGR (OpenCV), ou None se o vídeo acabou.
        """
        pass

    @abstractmethod
    def release(self):
        """
        Libera os recursos utilizados pela fonte de vídeo.
        """
        pass

    @property
    @abstractmethod
    def fps(self):
        """
        Retorna a taxa de quadros por segundo (FPS) da fonte.
        """
        pass

class FileVideoSource(VideoSource):
    """
    Implementação de fonte de vídeo a partir de um arquivo de vídeo.
    """
    
    def __init__(self, file_path):
        """
        Inicializa a fonte de vídeo a partir de um arquivo.
        
        Args:
            file_path (str): Caminho para o arquivo de vídeo.
        """
        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            raise ValueError(f"Não foi possível abrir o arquivo de vídeo: {file_path}")
        self._fps = self.cap.get(cv2.CAP_PROP_FPS)

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        self.cap.release()

    @property
    def fps(self):
        return self._fps

class ScreenVideoSource(VideoSource):
    """
    Implementação de fonte de vídeo a partir de captura de tela.
    """
    
    def __init__(self, monitor_index=1, bbox=None):
        """
        Inicializa a captura de tela.
        
        Args:
            monitor_index (int): Índice do monitor (1, 2, etc.).
            bbox (tuple): Área de captura (top, left, width, height). Se None, captura o monitor inteiro.
        """
        self.sct = mss.mss()
        # mss monitors: 0 é "todos", 1 é o primeiro, etc.
        print(f"[DEBUG] Monitores detectados: {len(self.sct.monitors)-1}")
        for i, m in enumerate(self.sct.monitors):
            print(f"[DEBUG] Monitor {i}: {m}")
            
        if monitor_index < len(self.sct.monitors):
             self.monitor = self.sct.monitors[monitor_index]
        else:
             print(f"[WARN] Monitor {monitor_index} não encontrado. Usando monitor 1.")
             self.monitor = self.sct.monitors[1]
        
        # Ajuste para garantir que a captura seja válida
        # Se bbox for fornecido, deve ser relativo ao monitor ou coordenadas globais?
        # MSS trata coordenadas como globais se não especificarmos monitor
        if bbox:
            # bbox: (x, y, w, h)
            self.monitor = {"top": bbox[1], "left": bbox[0], "width": bbox[2], "height": bbox[3]}
        
        self._fps = 30.0 # Valor estimado/alvo

    def get_frame(self):
        try:
            # grab retorna BGRA
            img = np.array(self.sct.grab(self.monitor))
            # Remove canal alpha
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            print(f"[ERRO] Falha na captura de tela: {e}")
            return None

    def release(self):
        self.sct.close()

    @property
    def fps(self):
        return self._fps
