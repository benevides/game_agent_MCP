from PIL import Image as PILImage
from PIL import ImageDraw  # pip install pillow
import io
import pygame #pip install pygame
import random
from mcp.server.fastmcp import FastMCP # pip install mcp
import base64


# Hand-drawn map layout (use '#' for wall, 'O' for open space)
MAP_LAYOUT_ORIGINAL = [
    "###########",
    "#OOOOOOOOO#",
    "#OOOOOOOOO#",
    "#OOOPOOOOO#",
    "#OOOOOOOOO#",
    "#OO#OOO#OO#",
    "#OOO###OOO#",
    "#OOOOOROOO#",
    "#OOOOOOOOO#",
    "#OOOOOOOOO#",
    "###########",
]
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


class Game:
    def __init__(self):
        # Sempre reinicia a partir do MAP_LAYOUT_ORIGINAL
        global MAP_LAYOUT
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

    def start(self):
        self.started = True
        self.show_reward_screen = False

    def reset(self):
        self.__init__()

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
        if self.player_pos == self.block_pos:
            self.score += 1
            self.show_reward_screen = True
            self.started = False

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

game = Game()

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
def ver_imagem() -> str:
    """Captura a tela atual do jogo, incluindo tela inicial, recompensa ou jogo."""
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
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Block Picker Game")
    clock = pygame.time.Clock()
    running = True
    brown = (139, 69, 19)
    open_color = (50, 50, 50)
    font = pygame.font.SysFont(None, 48)
    button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 40, 200, 80)


    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif not game.started:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button_rect.collidepoint(event.pos):
                        game.reset()
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

        if game.show_reward_screen:
            # Tela de recompensa
            msg_font = pygame.font.SysFont(None, 48)
            msg = msg_font.render("Você pegou a recompensa!", True, (255, 255, 255))
            msg_rect = msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
            screen.blit(msg, msg_rect)
            # Botão iniciar
            pygame.draw.rect(screen, (70, 130, 180), button_rect)
            text = font.render("Iniciar", True, (255, 255, 255))
            text_rect = text.get_rect(center=button_rect.center)
            screen.blit(text, text_rect)
        elif not game.started:
            # Tela inicial com botão
            pygame.draw.rect(screen, (70, 130, 180), button_rect)
            text = font.render("Iniciar", True, (255, 255, 255))
            text_rect = text.get_rect(center=button_rect.center)
            screen.blit(text, text_rect)
            title = font.render("Block Picker Game", True, (255, 255, 255))
            title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
            screen.blit(title, title_rect)
        else:
            # Move by MCP command
            if game.move_command:
                game.move_player(game.move_command)
                game.move_command = None

            game.update()

            # Draw map from MAP_LAYOUT
            for y, row in enumerate(MAP_LAYOUT):
                for x, cell in enumerate(row):
                    rect = (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                    if cell == '#':
                        pygame.draw.rect(screen, brown, rect)
                    else:
                        pygame.draw.rect(screen, open_color, rect)

            # Player and reward
            px, py = game.player_pos
            bx, by = game.block_pos
            pygame.draw.rect(screen, (0, 255, 0), (px * BLOCK_SIZE, py * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(screen, (255, 0, 0), (bx * BLOCK_SIZE, by * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

            # Draw score
            score_font = pygame.font.SysFont(None, 36)
            score_text = score_font.render(f'Score: {game.get_score()}', True, (255, 255, 255))
            screen.blit(score_text, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    import threading
    # Run MCP server in a separate thread
    threading.Thread(target=lambda: mcp.run(transport="sse"), daemon=True).start()
    main()
