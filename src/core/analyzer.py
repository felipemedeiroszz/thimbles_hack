class ThimblesAnalyzer:
    """
    Gerencia a lógica do jogo: quem tem a bola, onde ela está, etc.
    """
    def __init__(self):
        self.ball_bbox = None
        self.last_ball_bbox = None
        self.cup_bboxes = []
        self.target_cup_index = -1 # Índice do copo que contém a bola
        self.is_ball_hidden = False

    def initialize(self, ball_bbox, cup_bboxes):
        """
        Configura o estado inicial do jogo.
        
        Args:
            ball_bbox: (x, y, w, h) da bola. Pode ser None se não detectada.
            cup_bboxes: Lista de (x, y, w, h) dos copos.
        """
        self.ball_bbox = ball_bbox
        self.last_ball_bbox = ball_bbox
        self.cup_bboxes = cup_bboxes
        
        # Tenta associar a bola a um copo inicialmente
        if self.ball_bbox:
            self._assign_ball_to_cup()
        else:
            print("[WARN] Bola não detectada na inicialização. Selecione o copo que contém a bola se necessário.")

    def update(self, ball_bbox, cup_bboxes):
        """
        Atualiza o estado do jogo baseado nos novos rastreamentos.
        
        Args:
            ball_bbox: Nova posição da bola (ou None).
            cup_bboxes: Novas posições dos copos.
        """
        self.cup_bboxes = cup_bboxes
        
        if ball_bbox is not None:
            # Se a bola reapareceu longe do copo alvo anterior, pode ser um novo jogo
            # ou a bola saiu do copo.
            if self.is_ball_hidden and self.target_cup_index != -1:
                # Verifica se a bola está DENTRO do copo alvo atual
                if not self._is_ball_in_cup(ball_bbox, self.cup_bboxes[self.target_cup_index]):
                    # Se reapareceu FORA do copo alvo, reseta ou reavalia
                    print("[GAME] Bola reapareceu fora do copo alvo. Reavaliando...")
                    # Opcional: self.target_cup_index = -1 
            
            self.ball_bbox = ball_bbox
            self.last_ball_bbox = ball_bbox
            self.is_ball_hidden = False
            # Se a bola está visível, atualizamos quem a "possui" baseado na proximidade
            self._assign_ball_to_cup()
        else:
            # Se a bola acabou de sumir (estava visível antes)
            if not self.is_ball_hidden:
                 self._predict_entry_on_loss()
            
            self.is_ball_hidden = True
            # Se a bola está escondida, assumimos que ela continua no mesmo copo (target_cup_index)
            # O rastreador de copos cuida do movimento do copo.

    def _is_ball_in_cup(self, ball_box, cup_box):
        if not ball_box or not cup_box: return False
        bx, by, bw, bh = ball_box
        cx, cy, cw, ch = cup_box
        b_center_x = bx + bw / 2
        b_center_y = by + bh / 2
        return (cx <= b_center_x <= cx + cw) and (cy <= b_center_y <= cy + ch)

    def _predict_entry_on_loss(self):
        """
        Tenta adivinhar em qual copo a bola entrou se o rastreamento falhou.
        """
        if not self.last_ball_bbox:
            return

        bx, by, bw, bh = self.last_ball_bbox
        b_center_x = bx + bw / 2
        b_center_y = by + bh / 2
        
        closest_idx = -1
        min_dist = float('inf')
        
        for i, c_box in enumerate(self.cup_bboxes):
            if c_box is None: continue
            
            cx, cy, cw, ch = c_box
            c_center_x = cx + cw / 2
            c_center_y = cy + ch / 2
            
            # Distância entre centros
            dist = ((b_center_x - c_center_x)**2 + (b_center_y - c_center_y)**2)**0.5
            
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        
        # Se encontrou um copo, assume que entrou nele, 
        # a não ser que esteja absurdamente longe (ex: > 3x largura do copo)
        if closest_idx != -1 and self.cup_bboxes[closest_idx]:
             cw = self.cup_bboxes[closest_idx][2]
             
             # Limite bem generoso para garantir que capture
             if min_dist < cw * 3.5: 
                 print(f"[GAME] Bola perdida perto do copo #{closest_idx+1}. Assumindo entrada.")
                 self.target_cup_index = closest_idx
             else:
                 print(f"[DEBUG] Bola perdida longe dos copos (dist={min_dist:.1f}, cw={cw}). Nenhum alvo.")

    def _assign_ball_to_cup(self):
        """
        Verifica interseção entre a bola e os copos para determinar o 'dono' da bola.
        """
        if not self.ball_bbox:
            return

        bx, by, bw, bh = self.ball_bbox
        b_center_x = bx + bw / 2
        b_center_y = by + bh / 2

        # Verifica qual copo contém o centro da bola (ou está muito perto)
        for i, c_box in enumerate(self.cup_bboxes):
            if c_box is None: continue
            
            cx, cy, cw, ch = c_box
            
            # Margem de tolerância: bola pode estar um pouco fora do centro mas ainda "entrando"
            margin = 30 # Aumentei margem de entrada
            
            if (cx - margin <= b_center_x <= cx + cw + margin) and (cy - margin <= b_center_y <= cy + ch + margin):
                if self.target_cup_index != i:
                    print(f"[GAME] A bola entrou no copo #{i+1}")
                self.target_cup_index = i
                return
        
        # Se a bola está visível e NÃO está dentro de nenhum copo (nem perto), 
        # significa que ela está fora.
        
        # Vou forçar uma verificação extra: se a bola está visível e longe do copo alvo atual, perde o alvo.
        if self.target_cup_index != -1 and self.cup_bboxes[self.target_cup_index]:
             # Usando margem MUITO generosa para sair, para evitar "perder" o copo por um frame de ruído
             cx, cy, cw, ch = self.cup_bboxes[self.target_cup_index]
             margin_exit = 100 # Histerese muito alta: só sai se realmente se afastar
             
             if not ((cx - margin_exit <= b_center_x <= cx + cw + margin_exit) and 
                     (cy - margin_exit <= b_center_y <= cy + ch + margin_exit)):
                  # Saiu do copo!
                  # print("[GAME] Bola saiu do copo alvo.")
                  # self.target_cup_index = -1 # DESATIVADO: Só muda se entrar em outro copo!
                  pass

    def get_target_cup(self):
        """
        Retorna o índice e a bbox do copo que contém a bola.
        """
        if 0 <= self.target_cup_index < len(self.cup_bboxes):
            return self.target_cup_index, self.cup_bboxes[self.target_cup_index]
        return -1, None

    def set_target_cup_manually(self, index):
        """
        Força a definição de qual copo tem a bola (útil se a detecção automática falhar).
        """
        if 0 <= index < len(self.cup_bboxes):
            self.target_cup_index = index
            print(f"[GAME] Alvo definido manualmente: Copo #{index+1}")
