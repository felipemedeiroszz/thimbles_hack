import cv2
import sys
import os

# Adiciona o diretório atual ao path para importações funcionarem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from input.video_source import FileVideoSource, ScreenVideoSource
from core.detector import Detector
from core.tracker import MultiObjectTracker
from core.analyzer import ThimblesAnalyzer
from utils.visualizer import Visualizer
from utils.window_utils import get_window_rect

def main():
    use_screen = False
    video_path = None
    
    # Argumentos
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == "screen":
            use_screen = True
        elif os.path.exists(arg):
            video_path = arg
        else:
            # Se não é arquivo, pode ser parte do título da janela
            print(f"[INFO] Procurando janela com título: '{arg}'...")
            found_rect = get_window_rect(arg)
            if found_rect:
                print(f"[INFO] Janela encontrada! Área: {found_rect}")
                # Inicia direto com a área da janela
                start_live_tracking(found_rect)
                return
            else:
                print(f"[AVISO] Arquivo ou janela '{arg}' não encontrado. Usando modo seleção manual.")
                use_screen = True
    else:
        # Padrão: Tenta achar "Thimbles" ou "Casino" automaticamente
        print("[INFO] Buscando janela do jogo automaticamente...")
        # Tenta palavras chaves comuns
        # DETECÇÃO AUTOMÁTICA DESATIVADA POR PADRÃO PARA EVITAR ERROS DE JANELA OCULTA
        # O usuário prefere controle manual se algo der errado
        # for key in ["Thimbles", "Casino", "Chrome", "Edge", "Firefox"]:
        #     rect = get_window_rect(key)
        #     if rect:
        #         print(f"[INFO] Janela '{key}' detectada automaticamente.")
        #         start_live_tracking(rect)
        #         return
        
        print("[INFO] Detecção automática ignorada para garantir seleção correta.")
        print("[INFO] Usando seleção manual.")
        use_screen = True

    # 1. Inicialização (Modo Manual ou Arquivo)
    try:
        if use_screen:
            start_live_tracking(None)
        else:
            print(f"[INFO] Processando arquivo de vídeo: {video_path}")
            run_tracker(FileVideoSource(video_path))
            
    except ValueError as e:
        print(e)

def start_live_tracking(bbox):
    """
    Inicia o rastreamento em tempo real da tela.
    Se bbox for None, pede seleção manual.
    """
    if bbox:
        # Ajuste fino: mss precisa de inteiros
        bbox = tuple(map(int, bbox))
        source = ScreenVideoSource(monitor_index=1, bbox=bbox)
    else:
        # Captura inicial para seleção
        print("[INFO] Inicializando Modo AO VIVO...")
        temp_source = ScreenVideoSource(monitor_index=1)
        frame_full = temp_source.get_frame()
        temp_source.release()
        
        if frame_full is None:
            print("[ERRO] Falha ao acessar a tela. Frame vazio recebido.")
            return
        
        if frame_full.size == 0:
            print("[ERRO] Frame recebido com tamanho 0.")
            return
            
        print(f"[DEBUG] Frame capturado com sucesso: {frame_full.shape}")

        print("\n--- SELEÇÃO DA ÁREA DO JOGO ---")
        print(">> Desenhe um retângulo na área do jogo e aperte ENTER <<")
        
        h, w = frame_full.shape[:2]
        scale = 1.0
        if w > 1920:
            scale = 1920 / w
            frame_view = cv2.resize(frame_full, (1920, int(h * scale)))
        else:
            frame_view = frame_full.copy()
            
        # Adiciona instruções na tela
        cv2.putText(frame_view, "PASSO 1: SELECIONE APENAS A AREA DO JOGO", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        cv2.putText(frame_view, "Arraste o mouse e pressione ENTER ou ESPACO", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
        roi = cv2.selectROI("SELECIONE A AREA DO JOGO", frame_view, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("SELECIONE A AREA DO JOGO")
        
        if roi[2] == 0 or roi[3] == 0:
            print("[ERRO] Seleção inválida ou cancelada. É NECESSÁRIO selecionar a área do jogo para evitar espelhamento de tela.")
            print("[DICA] Execute o programa novamente e selecione apenas a região do navegador.")
            return
        else:
            if scale != 1.0:
                roi = tuple(int(v / scale) for v in roi)
            final_bbox = roi
            print(f"[INFO] Área definida: {final_bbox}")
            
            # Inicia captura restrita à área selecionada
            source = ScreenVideoSource(monitor_index=1, bbox=final_bbox)
            run_tracker(source)

def run_tracker(source):
    """Loop principal de rastreamento"""
    detector = Detector()
    tracker_cups = MultiObjectTracker(tracker_type='CSRT')
    analyzer = ThimblesAnalyzer()
    visualizer = Visualizer()

    print("[INFO] Iniciando Preview AO VIVO...")
    print(">>> Pressione 'S' para iniciar a configuração (Seleção de Objetos) <<<")

    # --- FASE 1: LIVE PREVIEW ---
    # Mostra o vídeo ao vivo até o usuário decidir configurar
    first_frame = None
    while True:
        frame = source.get_frame()
        if frame is None:
            print("[ERRO] Falha ao ler frame.")
            return

        # Redimensionar para visualização
        orig_height, orig_width = frame.shape[:2]
        scale_factor = 1.0
        if orig_width > 1280:
            scale_factor = 1280 / orig_width
            frame_disp = cv2.resize(frame, (1280, int(orig_height * scale_factor)))
        else:
            frame_disp = frame.copy()

        # Overlay de Instrução
        cv2.putText(frame_disp, "MODO PREVIEW - AGUARDANDO JOGO", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame_disp, "Pressione 'S' para Configurar Objetos", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow("Thimbles AI - MONITORAMENTO AO VIVO", frame_disp)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27: # ESC
            print("[INFO] Encerrando.")
            source.release()
            cv2.destroyAllWindows()
            return
        elif key == ord('s') or key == ord('S'):
            # Captura o frame ATUAL para usar na configuração
            first_frame = frame
            break
    
    # --- FASE 2: CONFIGURAÇÃO SIMPLIFICADA ---
    
    # Redimensionar frame de seleção também se necessário
    if scale_factor != 1.0:
        first_frame_disp = cv2.resize(first_frame, (1280, int(orig_height * scale_factor)))
    else:
        first_frame_disp = first_frame.copy()
        
    print("\n--- CONFIGURAÇÃO AUTOMÁTICA ---")
    print("Selecione a ÁREA RETANGULAR que engloba os 3 COPOS.")
    
    # Adiciona instrução visual
    cv2.putText(first_frame_disp, "PASSO 2: ARRASTE SOBRE OS 3 COPOS", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
    cv2.putText(first_frame_disp, "Pressione ENTER apos desenhar", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Seleção de área única para os copos usando selectROI (singular)
    # Isso evita o bug de criar múltiplas telas ou travar esperando ESC
    roi_rect_disp = detector.select_roi_manually(first_frame_disp, "2. Selecione a AREA DOS 3 COPOS (Enter)")
    
    if roi_rect_disp is None:
        print("[ERRO] Seleção cancelada. Voltando...")
        run_tracker(source)
        return

    # Converter coordenadas de volta para escala original
    def scale_bbox(bbox, factor):
        if not bbox: return None
        return tuple(int(v / factor) for v in bbox)
        
    roi_rect_orig = scale_bbox(roi_rect_disp, scale_factor)
    
    # Detecção Automática dos 3 Copos na Área
    print("[INFO] Detectando copos automaticamente na área...")
    cup_bboxes = detector.detect_cups_in_area(first_frame, roi_rect_orig)
    
    # SALVAR POSIÇÕES INICIAIS (HOME) para resetar em novos jogos
    initial_cups_bboxes = list(cup_bboxes)
    
    print(f"[INFO] {len(cup_bboxes)} copos identificados.")
    
    # Inicializar rastreador de copos
    tracker_cups.initialize(first_frame, cup_bboxes)
    
    # Bola começa como None (será detectada automaticamente)
    tracker_ball = None
    ball_bbox = None
    analyzer.initialize(None, cup_bboxes)

    # Calcular área média dos copos para servir de referência para a bola
    # A bola deve ser menor que um copo (ex: 50% da área)
    avg_cup_area = 0
    if len(cup_bboxes) > 0:
        total_area = sum([w*h for (_,_,w,h) in cup_bboxes])
        avg_cup_area = total_area / len(cup_bboxes)
    
    # Limite máximo para a bola (Aumentei para 120% para ser mais tolerante)
    max_ball_area = avg_cup_area * 1.2 if avg_cup_area > 0 else None

    print("\n[INFO] RASTREAMENTO INICIADO! Aguardando detecção da bola...")
    
    # --- FASE 3: LOOP DE RASTREAMENTO ---
    while True:
        frame = source.get_frame()
        if frame is None:
            break

        if scale_factor != 1.0:
             frame_disp = cv2.resize(frame, (1280, int(orig_height * scale_factor)))
        else:
             frame_disp = frame.copy() 

        # 1. Atualizar rastreadores dos COPOS primeiro (Referência)
        ok_cups, cups_boxes = tracker_cups.update(frame)

        # 2. Tentar detectar a bola se ainda não estiver rastreando
        # OU periodicamente para corrigir o tracker (Ressincronização)
        found_ball_color = detector.detect_ball_automatically(frame, max_area=max_ball_area)
        
        # LÓGICA DE RESET DOS COPOS (AUTO-CORREÇÃO DE DRIFT/SWAP)
        # Se a bola está visível (provável início/fim de jogo) e os copos estão PERTO das posições iniciais...
        if found_ball_color and initial_cups_bboxes:
             # Verificar se os copos atuais estão próximos das posições iniciais (HOME)
             is_at_home = True
             total_displacement = 0
             
             # Comparar box atual com box inicial (assumindo mesma ordem, mas verificando proximidade espacial geral)
             # Na verdade, precisamos saber se o "cenário" voltou ao normal.
             # Vamos checar se existe UM copo atual perto de CADA copo inicial.
             
             matched_count = 0
             for init_box in initial_cups_bboxes:
                 if not init_box: continue
                 ix, iy, iw, ih = init_box
                 icx, icy = ix + iw/2, iy + ih/2
                 
                 found_match = False
                 for curr_box in cups_boxes:
                     if not curr_box: continue
                     cx, cy, cw, ch = curr_box
                     ccx, ccy = cx + cw/2, cy + ch/2
                     
                     # Distância < 50 pixels
                     if ((icx - ccx)**2 + (icy - ccy)**2)**0.5 < 50:
                         found_match = True
                         break
                 if found_match:
                     matched_count += 1
             
             # Se todos os copos iniciais têm um correspondente atual próximo, o jogo resetou visualmente.
             # MAS os trackers podem estar trocados (swap).
             # Então forçamos um RESET COMPLETO dos trackers para garantir IDs corretos.
             if matched_count == len(initial_cups_bboxes) and len(initial_cups_bboxes) > 0:
                  # print("[DEBUG] Cenário resetado detectado. Reiniciando rastreadores de copos para corrigir trocas.")
                  tracker_cups.initialize(frame, initial_cups_bboxes)
                  cups_boxes = list(initial_cups_bboxes) # Atualiza boxes para o frame atual
                  ok_cups = True

        # FILTRO DE ZONA DE JOGO (NOVO): 
        # Ignorar detecções muito longe dos copos (verticalmente) para evitar botões
        if found_ball_color:
            bx, by, bw, bh = found_ball_color
            b_center_y = by + bh/2
            
            min_y = float('inf')
            max_y = float('-inf')
            has_cups = False
            
            for c_box in cups_boxes:
                if c_box:
                    cx, cy, cw, ch = c_box
                    if cy < min_y: min_y = cy
                    if cy + ch > max_y: max_y = cy + ch
                    has_cups = True
            
            if has_cups:
                # Aumentei a margem para 300px para garantir que pegue a bola em qualquer posição inicial
                margin_top = 300
                margin_bottom = 300
                
                if not ((min_y - margin_top) < b_center_y < (max_y + margin_bottom)):
                    # print(f"[DEBUG] Bola ignorada (fora da zona Y): {b_center_y}")
                    found_ball_color = None

        # Filtrar falsos positivos da bola se ela estiver "escondida"
        if analyzer.is_ball_hidden and found_ball_color:
            bx, by, bw, bh = found_ball_color
            b_center = (bx + bw/2, by + bh/2)
            
            is_noise = False
            for c_box in cups_boxes:
                if not c_box: continue
                cx, cy, cw, ch = c_box
                # Se o centro da "bola" estiver dentro de um copo, é provável que seja o próprio copo
                # (reflexo, detalhe vermelho, etc)
                if (cx < b_center[0] < cx+cw) and (cy < b_center[1] < cy+ch):
                    is_noise = True
                    break
            
            if is_noise:
                # print("[DEBUG] Ignorando detecção de bola dentro do copo (falso positivo)")
                found_ball_color = None

        ball_box_curr = None

        if tracker_ball is None:
            if found_ball_color:
                print("[INFO] BOLA DETECTADA! Iniciando rastreamento.")
                ball_bbox = found_ball_color
                tracker_ball = MultiObjectTracker(tracker_type='CSRT')
                tracker_ball.initialize(frame, [ball_bbox])
                analyzer.initialize(ball_bbox, cups_boxes) # Reinicia analyzer com a bola
                ball_box_curr = ball_bbox
            else:
                # Mensagem mais clara para o usuário
                cv2.putText(frame_disp, "JOGUE PARA REVELAR A BOLA", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # Se já estamos rastreando, verificamos se a detecção por cor diverge muito do tracker
            ok_ball, ball_boxes = tracker_ball.update(frame)
            
            # Caixa atual do tracker
            current_tracker_box = ball_boxes[0] if (ok_ball and len(ball_boxes) > 0) else None
            
            should_reset = False
            
            if found_ball_color:
                if current_tracker_box is None:
                    should_reset = True
                else:
                    t_box = current_tracker_box
                    # Calcular distância entre centro do tracker e centro da cor
                    tx, ty, tw, th = t_box
                    cx, cy, cw, ch = found_ball_color
                    
                    dist = ((tx+tw/2) - (cx+cw/2))**2 + ((ty+th/2) - (cy+ch/2))**2
                    # Se a distância for grande (ex: mais que 50 pixels), o tracker está errado ou é um novo jogo
                    if dist > 2500: # 50^2
                         print("[INFO] Ressincronizando tracker com detecção de cor...")
                         should_reset = True
            
            if should_reset and found_ball_color:
                ball_bbox = found_ball_color
                tracker_ball = MultiObjectTracker(tracker_type='CSRT')
                tracker_ball.initialize(frame, [ball_bbox])
                analyzer.update(ball_bbox, cups_boxes) # Atualiza analyzer forçadamente
                ball_box_curr = ball_bbox
            else:
                ball_box_curr = current_tracker_box

            # Se perdemos o tracker e não achamos cor, o ball_box_curr fica None, o que é correto (bola oculta ou perdida)
            if ball_box_curr is None and not found_ball_color:
                 tracker_ball = None # Encerra tracker se perdeu tudo 
        
        analyzer.update(ball_box_curr, cups_boxes)
        target_idx, _ = analyzer.get_target_cup()
        
        # Desenhar no frame de exibição (escalando as coordenadas)
        if scale_factor != 1.0:
            cups_boxes_disp = []
            for box in cups_boxes:
                if box: cups_boxes_disp.append(tuple(int(v * scale_factor) for v in box))
                else: cups_boxes_disp.append(None)
            
            ball_box_disp = tuple(int(v * scale_factor) for v in ball_box_curr) if ball_box_curr else None
        else:
            cups_boxes_disp = cups_boxes
            ball_box_disp = ball_box_curr

        visualizer.draw_tracking(frame_disp, cups_boxes_disp, ball_box_disp, target_idx, analyzer.is_ball_hidden)
        
        # Overlay de Status
        status_color = (0, 255, 0) if tracker_ball else (0, 255, 255)
        status_text = "EM JOGO" if tracker_ball else "AGUARDANDO BOLA"
        cv2.putText(frame_disp, f"STATUS: {status_text}", (10, orig_height - 20 if scale_factor == 1.0 else frame_disp.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        cv2.imshow("Thimbles AI - MONITORAMENTO AO VIVO", frame_disp)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27: # ESC
            break
        elif key == ord('r'): # Reset
            print("[INFO] Reiniciando configuração...")
            run_tracker(source)
            return

    source.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
