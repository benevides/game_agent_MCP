

import pygame # pip install pygame
import random
from mcp.server.fastmcp import FastMCP # pip install mcp

# Hand-drawn map layout (use '#' for wall, 'O' for open space)
MAP_LAYOUT = [
    "###########",
    "#OOOOOOOOO#",
    "#OOOOOOOOO#",
    "#OOOPOOOOO#",
    "#OOOOOOOOO#",
    "#######OOO#",
    "#OOOOOOOOO#",
    "#OOOROOOOO#",
    "#OOOOOOOOO#",
    "#OOOOOOOOO#",
    "###########",
]

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
        player_pos, reward_pos, cleaned_map = find_positions_and_clean_map()
        self.map_layout = cleaned_map
        global MAP_LAYOUT
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
            self.block_pos = self.random_block()

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
    return game.get_map()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Block Picker Game")
    clock = pygame.time.Clock()
    running = True
    brown = (139, 69, 19)
    open_color = (50, 50, 50)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    game.move_player('up')
                elif event.key == pygame.K_DOWN:
                    game.move_player('down')
                elif event.key == pygame.K_LEFT:
                    game.move_player('left')
                elif event.key == pygame.K_RIGHT:
                    game.move_player('right')

        # Move by MCP command
        if game.move_command:
            game.move_player(game.move_command)
            game.move_command = None

        game.update()

        screen.fill((30, 30, 30))

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
        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f'Score: {game.get_score()}', True, (255, 255, 255))
        screen.blit(score_text, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    import threading
    # Run MCP server in a separate thread
    threading.Thread(target=lambda: mcp.run(transport="sse"), daemon=True).start()
    main()
