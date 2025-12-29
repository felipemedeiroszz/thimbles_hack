import cv2

class MultiObjectTracker:
    """
    Gerencia múltiplos rastreadores de objetos para acompanhar os copos e a bolinha.
    """
    def __init__(self, tracker_type='CSRT'):
        """
        Args:
            tracker_type (str): Tipo de rastreador ('CSRT', 'KCF', etc.).
                                CSRT é mais preciso, KCF é mais rápido.
        """
        self.trackers = []
        self.tracker_type = tracker_type

    def _create_tracker(self):
        """Cria uma nova instância do rastreador baseada no tipo configurado."""
        tracker_type = self.tracker_type.upper()

        # Tenta criar usando a API padrão ou legacy (comum em versões recentes)
        try:
            if tracker_type == 'CSRT':
                if hasattr(cv2, 'TrackerCSRT_create'):
                    return cv2.TrackerCSRT_create()
                elif hasattr(cv2, 'legacy') and hasattr(cv2.legacy, 'TrackerCSRT_create'):
                    return cv2.legacy.TrackerCSRT_create()
                    
            elif tracker_type == 'KCF':
                if hasattr(cv2, 'TrackerKCF_create'):
                    return cv2.TrackerKCF_create()
                elif hasattr(cv2, 'legacy') and hasattr(cv2.legacy, 'TrackerKCF_create'):
                    return cv2.legacy.TrackerKCF_create()
                    
            elif tracker_type == 'MIL':
                if hasattr(cv2, 'TrackerMIL_create'):
                    return cv2.TrackerMIL_create()
                elif hasattr(cv2, 'legacy') and hasattr(cv2.legacy, 'TrackerMIL_create'):
                    return cv2.legacy.TrackerMIL_create()
                    
        except Exception as e:
            print(f"[ERRO] Falha ao criar tracker: {e}")

        # Fallback ou erro explicativo
        print(f"[ERRO] Rastreador '{tracker_type}' não encontrado nesta versão do OpenCV.")
        print("[SOLUÇÃO] Instalando dependências extras...")
        raise AttributeError(f"cv2.Tracker{tracker_type}_create not found. Install opencv-contrib-python.")

    def initialize(self, frame, bboxes):
        """
        Inicializa rastreadores para uma lista de bounding boxes.
        Limpa rastreadores anteriores.
        
        Args:
            frame: Frame inicial.
            bboxes: Lista de tuplas (x, y, w, h).
        """
        self.trackers = []
        for bbox in bboxes:
            tracker = self._create_tracker()
            tracker.init(frame, bbox)
            self.trackers.append(tracker)
        print(f"[INFO] {len(self.trackers)} rastreadores inicializados.")

    def update(self, frame):
        """
        Atualiza a posição de todos os objetos rastreados.
        
        Args:
            frame: O frame atual do vídeo.
            
        Returns:
            tuple: (success_flag, list_of_boxes)
                   success_flag é True se todos os objetos foram rastreados com sucesso.
                   list_of_boxes contém as novas posições (x, y, w, h) ou None para objetos perdidos.
        """
        boxes = []
        all_ok = True
        
        for i, tracker in enumerate(self.trackers):
            ok, box = tracker.update(frame)
            if ok:
                # Converte para int para facilitar desenho depois
                box = tuple(map(int, box))
                boxes.append(box)
            else:
                all_ok = False
                boxes.append(None)
                # print(f"[WARN] Objeto {i} perdido.")
        
        return all_ok, boxes
