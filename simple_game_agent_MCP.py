import pygame
import random
from mcp.server.fastmcp import FastMCP

# Game settings
WIDTH, HEIGHT = 400, 400
BLOCK_SIZE = 40
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

class Game:
    def __init__(self):
        rows = HEIGHT // BLOCK_SIZE
        cols = WIDTH // BLOCK_SIZE
        # Player começa no centro, mas nunca em cima da cerca
        px, py = cols // 2, rows // 2
        if px == 0: px = 1
        if py == 0: py = 1
        self.player_pos = [px * BLOCK_SIZE, py * BLOCK_SIZE]
        self.block_pos = self.random_block()
        self.score = 0
        self.move_command = None

    def random_block(self):
        rows = HEIGHT // BLOCK_SIZE
        cols = WIDTH // BLOCK_SIZE
        while True:
            x = random.randint(1, cols - 2) * BLOCK_SIZE
            y = random.randint(1, rows - 2) * BLOCK_SIZE
            # Garante que não gera em cima da cerca
            if [x, y] != self.player_pos:
                return [x, y]

    def move_player(self, direction):
        if direction in DIRECTIONS:
            dx, dy = DIRECTIONS[direction]
            new_x = self.player_pos[0] + dx * BLOCK_SIZE
            new_y = self.player_pos[1] + dy * BLOCK_SIZE
            rows = HEIGHT // BLOCK_SIZE
            cols = WIDTH // BLOCK_SIZE
            # Verifica limites e se não é cerca
            col = new_x // BLOCK_SIZE
            row = new_y // BLOCK_SIZE
            if 1 <= col < cols-1 and 1 <= row < rows-1:
                self.player_pos = [new_x, new_y]

    def update(self):
        if self.player_pos == self.block_pos:
            self.score += 1
            self.block_pos = self.random_block()

    def set_move(self, direction):
        self.move_command = direction

    def get_score(self):
        return self.score

    def get_map(self):
        """Retorna uma string representando o mapa do jogo com cerca (#), O para livre, P para player e R para recompensa."""
        rows = HEIGHT // BLOCK_SIZE
        cols = WIDTH // BLOCK_SIZE
        grid = [['O' for _ in range(cols)] for _ in range(rows)]
        # Cerca nas extremidades
        for y in range(rows):
            grid[y][0] = '#'
            grid[y][cols-1] = '#'
        for x in range(cols):
            grid[0][x] = '#'
            grid[rows-1][x] = '#'
        # Player e recompensa
        px, py = self.player_pos[0] // BLOCK_SIZE, self.player_pos[1] // BLOCK_SIZE
        bx, by = self.block_pos[0] // BLOCK_SIZE, self.block_pos[1] // BLOCK_SIZE
        grid[py][px] = 'P'
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
def mapa() -> str:
    """Retorna o desenho do mapa atual (P=player, R=recompensa, espaço=livre)."""
    return game.get_map()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Block Picker Game")
    clock = pygame.time.Clock()
    running = True

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

        # Desenha cerca (marrom) apenas nas laterais
        rows = HEIGHT // BLOCK_SIZE
        cols = WIDTH // BLOCK_SIZE
        brown = (139, 69, 19)
        # Extremidades
        for y in range(rows):
            pygame.draw.rect(screen, brown, (0, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(screen, brown, ((cols-1) * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
        for x in range(cols):
            pygame.draw.rect(screen, brown, (x * BLOCK_SIZE, 0, BLOCK_SIZE, BLOCK_SIZE))
            pygame.draw.rect(screen, brown, (x * BLOCK_SIZE, (rows-1) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

        # Player e recompensa
        pygame.draw.rect(screen, (0, 255, 0), (*game.player_pos, BLOCK_SIZE, BLOCK_SIZE))
        pygame.draw.rect(screen, (255, 0, 0), (*game.block_pos, BLOCK_SIZE, BLOCK_SIZE))

        # Escreve o score na tela
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
