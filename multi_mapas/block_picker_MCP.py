from PIL import Image as PILImage
from PIL import ImageDraw  # pip install pillow
import io
import pygame #pip install pygame
import random
from mcp.server.fastmcp import FastMCP # pip install mcp
import base64
from game_maps import MAPS


# Hand-drawn map layout (use '#' for wall, 'O' for open space)
MAP_LAYOUT_ORIGINAL = MAPS[0]["layout"]
MAP_LAYOUT = list(MAP_LAYOUT_ORIGINAL)

BLOCK_SIZE = 40
ROWS = len(MAP_LAYOUT)
COLS = len(MAP_LAYOUT[0])
WIDTH, HEIGHT = COLS * BLOCK_SIZE, ROWS * BLOCK_SIZE
FPS = 10

# Directions
DIRECTIONS = {
    'up': (0, -1),
    'down': (0, 1),
    'left': (-1, 0),
    'right': (1, 0)
}

# MCP server
mcp = FastMCP("Block Picker Game")


def find_positions_and_clean_map():
    player_pos = None
    reward_pos = None
    new_map = []
    for y, row in enumerate(MAP_LAYOUT):
        new_row = list(row)
        for x, cell in enumerate(row):
            if cell == 'P':
                player_pos = [x, y]
                new_row[x] = 'O'
            elif cell == 'R':
                reward_pos = [x, y]
                new_row[x] = 'O'
        new_map.append(''.join(new_row))
    return player_pos, reward_pos, new_map


def draw_checkbox(screen, checked, rect, font):
    pygame.draw.rect(screen, (220, 220, 220), rect)
    pygame.draw.rect(screen, (0, 0, 0), rect, 2)
    if checked:
        pygame.draw.line(screen, (0, 0, 0), (rect.x + 5, rect.y + 5), (rect.x + rect.width - 5, rect.y + rect.height - 5), 3)
        pygame.draw.line(screen, (0, 0, 0), (rect.x + rect.width - 5, rect.y + 5), (rect.x + 5, rect.y + rect.height - 5), 3)
    label = font.render("Sequencial", True, (0, 0, 0))
    label_pos = (rect.x + rect.width + 10, rect.y)
    label_bg_rect = pygame.Rect(label_pos[0] - 4, label_pos[1] - 2, label.get_width() + 8, label.get_height() + 4)
    pygame.draw.rect(screen, (180, 220, 255), label_bg_rect)
    screen.blit(label, label_pos)


class Game:
    def __init__(self, map_idx=0):
        global MAP_LAYOUT, MAP_LAYOUT_ORIGINAL, selected_map_idx
        self.map_idx = map_idx
        selected_map_idx = map_idx
        MAP_LAYOUT_ORIGINAL = MAPS[self.map_idx]["layout"]
        MAP_LAYOUT = list(MAP_LAYOUT_ORIGINAL)
        player_pos, reward_pos, cleaned_map = find_positions_and_clean_map()
        self.map_layout = cleaned_map
        MAP_LAYOUT = self.map_layout  # update global for rendering
        # Player
        if player_pos:
            self.player_pos = player_pos
        else:
            self.player_pos = self.find_first_open()
        # Reward
        if reward_pos:
            self.block_pos = reward_pos
        else:
            self.block_pos = self.random_block()
        self.score = 0
        self.move_command = None
        self.started = False  # se está jogando
        self.show_reward_screen = False  # se mostra tela de recompensa
        self.in_transition = False
        self.transition_start = None

    def start(self):
        self.started = True
        self.show_reward_screen = False
        self.in_transition = False
        self.transition_start = None

    def reset(self, map_idx=None):
        if map_idx is None:
            map_idx = self.map_idx
        self.__init__(map_idx)

    def find_first_open(self):
        for y, row in enumerate(self.map_layout):
            for x, cell in enumerate(row):
                if cell == 'O':
                    return [x, y]
        return [1, 1]  # fallback

    def random_block(self):
        while True:
            x = random.randint(0, COLS - 1)
            y = random.randint(0, ROWS - 1)
            if self.map_layout[y][x] == 'O' and [x, y] != self.player_pos:
                return [x, y]

    def move_player(self, direction):
        if direction in DIRECTIONS:
            dx, dy = DIRECTIONS[direction]
            new_x = self.player_pos[0] + dx
            new_y = self.player_pos[1] + dy
            if 0 <= new_x < COLS and 0 <= new_y < ROWS:
                if self.map_layout[new_y][new_x] == 'O':
                    self.player_pos = [new_x, new_y]

    def update(self):
        global selected_map_idx, game, MAP_LAYOUT_ORIGINAL, MAP_LAYOUT, ROWS, COLS, WIDTH, HEIGHT, sequencial_mode, transition_timer, all_maps_completed
        if self.player_pos == self.block_pos:
            self.score += 1
            self.show_reward_screen = True
            self.started = False
            if sequencial_mode:
                # Se modo sequencial, inicia transição
                self.in_transition = True
                self.transition_start = pygame.time.get_ticks()
                transition_timer = self.transition_start
                # Se último mapa, marca todos completos
                if selected_map_idx == len(MAPS) - 1:
                    all_maps_completed = True
            else:
                # Modo normal: não faz nada especial
                pass

    def next_map(self):
        global selected_map_idx, game, MAP_LAYOUT_ORIGINAL, MAP_LAYOUT, ROWS, COLS, WIDTH, HEIGHT, all_maps_completed
        selected_map_idx += 1
        if selected_map_idx >= len(MAPS):
            all_maps_completed = True
            selected_map_idx = 0
            game.reset(selected_map_idx)
            return
        MAP_LAYOUT_ORIGINAL = MAPS[selected_map_idx]["layout"]
        MAP_LAYOUT = list(MAP_LAYOUT_ORIGINAL)
        ROWS = len(MAP_LAYOUT)
        COLS = len(MAP_LAYOUT[0])
        WIDTH, HEIGHT = COLS * BLOCK_SIZE, ROWS * BLOCK_SIZE
        game = Game(selected_map_idx)
        game.start()

    def set_move(self, direction):
        self.move_command = direction
        print("Moveu ", direction)

    def get_score(self):
        return self.score

    def get_map(self):
        """Retorna uma string representando o mapa do jogo com cerca (#), O para livre, P para player e R para recompensa."""
        grid = [list(row) for row in self.map_layout]
        px, py = self.player_pos
        bx, by = self.block_pos
        if grid[py][px] == 'O':
            grid[py][px] = 'P'
        if grid[by][bx] == 'O':
            grid[by][bx] = 'R'
        print("grid\n", grid)
        return '\n'.join(''.join(row) for row in grid)

selected_map_idx = 0
sequencial_mode = False
transition_timer = None
all_maps_completed = False
game = Game(selected_map_idx)

@mcp.tool()
def mover(direcao: str) -> str:
    """Move o jogador na direção especificada (up, down, left, right)."""
    if direcao in DIRECTIONS:
        game.set_move(direcao)
        return f"Movendo para {direcao}"
    else:
        return "Direção inválida. Use: up, down, left, right."

@mcp.tool()
def pontuacao() -> str:
    """Retorna a pontuação atual do jogador."""
    return f"Pontuação: {game.get_score()}"


@mcp.tool()
def pedir_mapa() -> str:
    """Retorna o desenho do mapa atual (P=player, R=recompensa, O=livre, #=bloqueado)."""
    if not game.started and not game.show_reward_screen:
        return "O jogo ainda não foi iniciado. Use o botão ou a ferramenta 'iniciar_jogo' para começar."
    if game.show_reward_screen:
        return "Parabéns! Você pegou a recompensa. Clique em 'Iniciar' para jogar novamente."
    return game.get_map()


@mcp.tool()
def ver_mapa_em_JPG() -> str:
    """Captura a tela atual do jogo no formato JPG, incluindo tela inicial, recompensa ou jogo."""
    import pygame.surfarray
    # A tela do pygame deve estar criada e visível
    screen = pygame.display.get_surface()
    if screen is None:
        return "Tela não disponível."
    # Captura a tela como array
    arr = pygame.surfarray.array3d(screen)
    # Transforma para PIL (precisa transpor e inverter eixo)
    img = PILImage.fromarray(arr.swapaxes(0, 1))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
    return img_base64


@mcp.tool()
def iniciar_jogo() -> str:
    """Inicia ou reinicia o jogo (igual ao botão Iniciar da tela). Só funciona na tela inicial ou de recompensa."""
    if game.started:
        return "O jogo já está em andamento. Só é possível iniciar na tela inicial ou após pegar a recompensa."
    if not game.started or game.show_reward_screen:
        game.reset()
        game.start()
        return "Jogo iniciado!"
    return "Só é possível iniciar na tela inicial ou após pegar a recompensa."


def main():
    pygame.init()
    global MAP_LAYOUT_ORIGINAL, MAP_LAYOUT, ROWS, COLS, WIDTH, HEIGHT, game, sequencial_mode, transition_timer, all_maps_completed, selected_map_idx
    screen = pygame.display.set_mode((WIDTH, HEIGHT + 60))
    pygame.display.set_caption("Block Picker Game")
    clock = pygame.time.Clock()
    running = True
    brown = (139, 69, 19)
    open_color = (50, 50, 50)
    font = pygame.font.SysFont(None, 32)
    button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 40, 200, 80)
    dropdown_rect = pygame.Rect(10, 10, 200, 40)
    dropdown_open = False
    checkbox_rect = pygame.Rect(230, 10, 30, 30)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                dropdown_handled = False
                show_dropdown = (not game.started) or game.show_reward_screen
                if show_dropdown:
                    if dropdown_rect.collidepoint(event.pos):
                        dropdown_open = not dropdown_open
                        dropdown_handled = True
                    elif dropdown_open:
                        for i, m in enumerate(MAPS):
                            option_rect = pygame.Rect(10, 10 + 40 * (i + 1), 200, 40)
                            if option_rect.collidepoint(event.pos):
                                selected_map_idx = i
                                MAP_LAYOUT_ORIGINAL = MAPS[selected_map_idx]["layout"]
                                MAP_LAYOUT = list(MAP_LAYOUT_ORIGINAL)
                                ROWS = len(MAP_LAYOUT)
                                COLS = len(MAP_LAYOUT[0])
                                WIDTH, HEIGHT = COLS * BLOCK_SIZE, ROWS * BLOCK_SIZE
                                game = Game(selected_map_idx)
                                dropdown_open = False
                                screen = pygame.display.set_mode((WIDTH, HEIGHT + 60))
                                dropdown_handled = True
                                break
                    # Checkbox click
                    if checkbox_rect.collidepoint(event.pos):
                        sequencial_mode = not sequencial_mode
                        dropdown_handled = True
                if not dropdown_handled and not game.started:
                    if button_rect.collidepoint(event.pos):
                        game.reset(selected_map_idx)
                        game.start()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    game.move_player('up')
                elif event.key == pygame.K_DOWN:
                    game.move_player('down')
                elif event.key == pygame.K_LEFT:
                    game.move_player('left')
                elif event.key == pygame.K_RIGHT:
                    game.move_player('right')

        screen.fill((30, 30, 30))

        # Sequencial mode: transition screen
        if sequencial_mode and game.in_transition:
            elapsed = pygame.time.get_ticks() - game.transition_start
            msg_font = pygame.font.SysFont(None, 48)
            if all_maps_completed:
                msg = msg_font.render("Todos os mapas completos!", True, (255, 255, 255))
                msg_rect = msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
                screen.blit(msg, msg_rect)
                # Volta ao menu inicial após 3 segundos
                if elapsed > 3000:
                    all_maps_completed = False
                    game.reset(0)
                    dropdown_open = False
            else:
                msg = msg_font.render("Próximo mapa...", True, (255, 255, 255))
                msg_rect = msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
                screen.blit(msg, msg_rect)
                if elapsed > 3000:
                    game.in_transition = False
                    game.next_map()
                    dropdown_open = False
            pygame.display.flip()
            clock.tick(FPS)
            continue

        if game.show_reward_screen:
            msg_font = pygame.font.SysFont(None, 48)
            # Move message higher so button does not cover it
            msg = msg_font.render("Você pegou a recompensa!", True, (255, 255, 255))
            msg_rect = msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 120))
            screen.blit(msg, msg_rect)
            pygame.draw.rect(screen, (70, 130, 180), button_rect)
            text = font.render("Iniciar", True, (255, 255, 255))
            text_rect = text.get_rect(center=button_rect.center)
            screen.blit(text, text_rect)
        elif not game.started:
            pygame.draw.rect(screen, (70, 130, 180), button_rect)
            text = font.render("Iniciar", True, (255, 255, 255))
            text_rect = text.get_rect(center=button_rect.center)
            screen.blit(text, text_rect)
            title = font.render("Block Picker Game", True, (255, 255, 255))
            title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
            screen.blit(title, title_rect)
        else:
            if game.move_command:
                game.move_player(game.move_command)
                game.move_command = None
            game.update()
            for y, row in enumerate(MAP_LAYOUT):
                for x, cell in enumerate(row):
                    rect = (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                    if cell == '#':
                        pygame.draw.rect(screen, brown, rect)
                    else:
                        pygame.draw.rect(screen, open_color, rect)
            px, py = game.player_pos
            bx, by = game.block_pos
            pygame.draw.rect(screen, (0, 255, 0), (px * BLOCK_SIZE, py * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(screen, (255, 0, 0), (bx * BLOCK_SIZE, by * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
            score_font = pygame.font.SysFont(None, 36)
            score_text = score_font.render(f'Score: {game.get_score()}', True, (255, 255, 255))
            screen.blit(score_text, (10, 10))

        # Draw dropdown menu and checkbox only if not started or reward screen
        show_dropdown = (not game.started) or game.show_reward_screen
        if show_dropdown:
            pygame.draw.rect(screen, (200, 200, 200), dropdown_rect)
            map_name = MAPS[selected_map_idx]["name"]
            text = font.render(map_name, True, (0, 0, 0))
            screen.blit(text, (dropdown_rect.x + 10, dropdown_rect.y + 5))
            pygame.draw.polygon(screen, (0, 0, 0), [
                (dropdown_rect.right - 20, dropdown_rect.y + 15),
                (dropdown_rect.right - 10, dropdown_rect.y + 15),
                (dropdown_rect.right - 15, dropdown_rect.y + 25)
            ])
            if dropdown_open:
                for i, m in enumerate(MAPS):
                    option_rect = pygame.Rect(10, 10 + 40 * (i + 1), 200, 40)
                    pygame.draw.rect(screen, (220, 220, 220), option_rect)
                    option_text = font.render(m["name"], True, (0, 0, 0))
                    screen.blit(option_text, (option_rect.x + 10, option_rect.y + 5))
            # Draw checkbox
            draw_checkbox(screen, sequencial_mode, checkbox_rect, font)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    import threading
    # Run MCP server in a separate thread
    threading.Thread(target=lambda: mcp.run(transport="sse"), daemon=True).start()
    main()
