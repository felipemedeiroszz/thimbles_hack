import cv2
import numpy as np

class Detector:
    """
    Responsável por detectar objetos (copos e bolinha) no frame.
    """
    
    def __init__(self):
        pass

    def select_roi_manually(self, frame, message="Selecione a area (Enter para confirmar)"):
        """
        Permite selecionar UMA ÚNICA região de interesse.
        Mais simples e menos propenso a erros que selectROIs.
        """
        print(f"[INFO] {message}")
        # selectROI retorna apenas uma tupla (x,y,w,h)
        # O fluxo é: desenha -> ENTER/ESPAÇO -> retorna
        bbox = cv2.selectROI(message, frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(message)
        
        # Se largura ou altura for 0, o usuário cancelou ou fez errado
        if bbox[2] == 0 or bbox[3] == 0:
            return None
        return bbox

    def select_rois_manually(self, frame, message="Selecione os objetos (Enter para confirmar, Esc para sair)"):
        """
        Permite ao usuário selecionar manualmente as regiões de interesse (ROIs).
        Útil para inicializar os rastreadores no início do jogo.
        
        Args:
            frame: O frame de vídeo onde a seleção será feita.
            message: Mensagem a ser exibida na janela.
            
        Returns:
            list: Lista de tuplas (x, y, w, h) das bounding boxes selecionadas.
        """
        print(f"[INFO] {message}")
        # cv2.selectROIs permite selecionar múltiplos objetos
        # O usuário desenha caixas e pressiona ENTER ou ESPAÇO para adicionar
        # Pressiona ESC para terminar a seleção
        bboxes = cv2.selectROIs(message, frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(message)
        return bboxes

    def detect_cups_in_area(self, frame, roi_rect):
        """
        Detecta automaticamente 3 copos dentro de uma área selecionada.
        
        Args:
            frame: Frame completo.
            roi_rect: (x, y, w, h) da área onde estão os copos.
            
        Returns:
            list: Lista de 3 tuplas (x, y, w, h) ordenadas da esquerda para a direita.
        """
        x_roi, y_roi, w_roi, h_roi = roi_rect
        roi = frame[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
        
        # Converter para escala de cinza e aplicar threshold
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Blur para reduzir ruído
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detecção de bordas ou threshold adaptativo
        # Thimbles costumam ter bordas bem definidas ou contraste
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilatar para fechar bordas
        kernel = np.ones((3,3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos que parecem copos
        # Critérios: Área mínima, aspecto (geralmente mais altos que largos ou quadrados)
        candidates = []
        min_area = (w_roi * h_roi) * 0.02 # 2% da área total da ROI
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                # Ajustar coordenadas para o frame original
                candidates.append((x + x_roi, y + y_roi, w, h))
        
        # Filtrar candidatos sobrepostos ou muito próximos
        final_candidates = []
        for cand in candidates:
            cx = cand[0] + cand[2]/2
            cy = cand[1] + cand[3]/2
            
            is_new = True
            for existing in final_candidates:
                ex = existing[0] + existing[2]/2
                ey = existing[1] + existing[3]/2
                
                # Distância entre centros
                dist = ((cx - ex)**2 + (cy - ey)**2)**0.5
                
                # Se a distância for menor que a largura do copo existente (assumindo sobreposição), ignora
                if dist < existing[2]:
                    is_new = False
                    break
            
            if is_new:
                final_candidates.append(cand)

        # Ordenar candidatos por área (maior para menor) e pegar os 3 maiores
        final_candidates.sort(key=lambda b: b[2]*b[3], reverse=True)
        top_3 = final_candidates[:3]
        
        # Se não achou 3, tenta usar heurística de divisão da área
        # IMPORTANTE: Se achou menos que 3, a divisão da área é mais segura que detecção parcial
        if len(top_3) < 3:
            print(f"[AVISO] Apenas {len(top_3)} copos detectados por contorno. Usando divisão da área.")
            # Dividir a ROI em 3 partes iguais horizontalmente
            cup_w = w_roi // 3
            top_3 = [
                (x_roi, y_roi, cup_w, h_roi),
                (x_roi + cup_w, y_roi, cup_w, h_roi),
                (x_roi + 2*cup_w, y_roi, cup_w, h_roi)
            ]
        
        # Ordenar final da esquerda para a direita (x crescente)
        top_3.sort(key=lambda b: b[0])
        
        return top_3

    def detect_ball_automatically(self, frame, max_area=None):
        """
        Procura pela bolinha vermelha em todo o frame.
        Filtra por formato e tamanho para evitar falsos positivos (como botões).
        """
        # Intervalo de cor para vermelho (HSV)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Vermelho baixo
        lower_red1 = np.array([0, 120, 70])
        upper_red1 = np.array([10, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        
        # Vermelho alto
        lower_red2 = np.array([170, 120, 70])
        upper_red2 = np.array([180, 255, 255])
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        mask = mask1 + mask2
        
        # Limpeza
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_candidates = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filtro de área mínima
            if area < 50: continue
            
            # Filtro de área máxima (se fornecida, ex: menor que um copo)
            if max_area and area > max_area: continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            
            # Filtro de formato: A bolinha deve ser quase quadrada/circular
            # Aceita entre 0.6 e 1.6 (tolerância para movimento/blur)
            if 0.6 <= aspect_ratio <= 1.6:
                valid_candidates.append((area, (x, y, w, h)))
        
        if valid_candidates:
            # Ordena por área (maior primeiro) e pega o maior candidato válido
            # Geralmente a bola é o maior objeto vermelho "redondo" na tela (excluindo botões largos)
            valid_candidates.sort(key=lambda x: x[0], reverse=True)
            return valid_candidates[0][1]
                
        return None
