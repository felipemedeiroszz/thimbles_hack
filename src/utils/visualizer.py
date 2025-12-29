import cv2

class Visualizer:
    """
    Responsável por desenhar informações visuais no frame.
    """
    
    @staticmethod
    def draw_tracking(frame, cup_bboxes, ball_bbox, target_cup_index, is_ball_hidden):
        """
        Desenha as bounding boxes dos copos e da bola, destacando o alvo.
        
        Args:
            frame: O frame atual.
            cup_bboxes: Lista de bboxes dos copos.
            ball_bbox: Bbox da bola (ou None).
            target_cup_index: Índice do copo alvo.
            is_ball_hidden: Booleano indicando se a bola está escondida.
        """
        # Desenha os copos
        for i, bbox in enumerate(cup_bboxes):
            if bbox is not None:
                # SÓ DESENHA SE FOR O ALVO (Solicitação do usuário: "apenas o copo que esta a bolinha precisa ficar marcado")
                if i == target_cup_index:
                    x, y, w, h = map(int, bbox)
                    color = (0, 255, 0) # Verde
                    thickness = 4
                    label = f"BOLA AQUI"
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
                    cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3)
                    
                    # Desenhar "Ghost Ball" se a bola estiver escondida para confirmar visualmente
                    if is_ball_hidden:
                         cv2.circle(frame, (x + w//2, y + h//2 + 20), 15, (0, 0, 255), -1) # Bola vermelha virtual
                else:
                    # Desenhar contorno sutil para os outros copos para mostrar que o sistema ainda está rastreando
                    # mas sem "marcar" como alvo. Apenas feedback visual de funcionamento.
                    x, y, w, h = map(int, bbox)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (200, 200, 200), 1) # Cinza claro, fino

        # Desenha a bola se visível (detectada pelo sistema)
        if ball_bbox is not None:
            x, y, w, h = map(int, ball_bbox)
            # Box Magenta para destacar bem a bola detectada
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 255), 3) 
            cv2.putText(frame, "BOLA DETECTADA", (x, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        
        # Info na tela
        status = "Bola: ESCONDIDA" if is_ball_hidden else "Bola: VISIVEL"
        cv2.putText(frame, f"Status: {status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame
