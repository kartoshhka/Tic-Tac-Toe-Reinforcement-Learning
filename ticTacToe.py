import numpy as np
import pickle

BOARD_ROWS = 3
BOARD_COLS = 3


class State:
    def __init__(self, p1, p2):
        self.board = np.zeros((BOARD_ROWS, BOARD_COLS))
        self.p1 = p1
        self.p2 = p2
        self.isEnd = False
        self.boardHash = None
       # p1 делает первый ход
        self.playerSymbol = 1
    
    # хешируем состояние поля
    def getHash(self):
        self.boardHash = str(self.board.reshape(BOARD_COLS*BOARD_ROWS))
        return self.boardHash
    
    def winner(self):
        # проверяем строки
        for i in range(BOARD_ROWS):
            if sum(self.board[i, :]) == 3:
                self.isEnd = True
                return 1
            if sum(self.board[i, :]) == -3:
                self.isEnd = True
                return -1
        # проверяем столбцы
        for i in range(BOARD_COLS):
            if sum(self.board[:, i]) == 3:
                self.isEnd = True
                return 1
            if sum(self.board[:, i]) == -3:
                self.isEnd = True
                return -1
        # проверяем диагонали
        diag_sum1 = sum([self.board[i, i] for i in range(BOARD_COLS)])
        diag_sum2 = sum([self.board[i, BOARD_COLS-i-1] for i in range(BOARD_COLS)])
        diag_sum = max(diag_sum1, diag_sum2)
        if diag_sum == 3:
            self.isEnd = True
            return 1
        if diag_sum == -3:
            self.isEnd = True
            return -1
        
        # ничья
        # нет доступных позиций
        if len(self.availablePositions()) == 0:
            self.isEnd = True
            return 0
        # игра не закончена
        self.isEnd = False
        return None
    
    def availablePositions(self):
        positions = []
        for i in range(BOARD_ROWS):
            for j in range(BOARD_COLS):
                if self.board[i, j] == 0:
                    positions.append((i, j))  # должен быть кортежем
        return positions
    
    def updateState(self, position):
        self.board[position] = self.playerSymbol
        # переключение на другого игрока
        self.playerSymbol = -1 if self.playerSymbol == 1 else 1
    
    # только если игра закончена
    def giveReward(self):
        result = self.winner()
        # вознаграждение
        if result == 1:
            self.p1.feedReward(1)
            self.p2.feedReward(0)
        elif result == -1:
            self.p1.feedReward(0)
            self.p2.feedReward(1)
        else:
            self.p1.feedReward(0.1)
            self.p2.feedReward(0.5)
    
    # обновление поля
    def reset(self):
        self.board = np.zeros((BOARD_ROWS, BOARD_COLS))
        self.boardHash = None
        self.isEnd = False
        self.playerSymbol = 1
    
    def play(self, rounds=100):
        for i in range(rounds):
            if i%1000 == 0:
                print("Сыграно игр: {}".format(i))
            while not self.isEnd:
                # Player 1
                positions = self.availablePositions()
                p1_action = self.p1.chooseAction(positions, self.board, self.playerSymbol)
                # выполняем действие и обновляем состояние поля
                self.updateState(p1_action)
                board_hash = self.getHash()
                self.p1.addState(board_hash)
                
                # проверяем, не закончилась ли игра
                win = self.winner()
                if win is not None:
                    # self.showBoard()
                    # игра закончилась победой игрока p1 или ничьей
                    self.giveReward()
                    self.p1.reset()
                    self.p2.reset()
                    self.reset()
                    break

                else:
                    # Player 2
                    positions = self.availablePositions()
                    p2_action = self.p2.chooseAction(positions, self.board, self.playerSymbol)
                    self.updateState(p2_action)
                    board_hash = self.getHash()
                    self.p2.addState(board_hash)
                    
                    win = self.winner()
                    if win is not None:
                        # self.showBoard()
                        # игра закончилась победой игрока p2 или ничьей
                        self.giveReward()
                        self.p1.reset()
                        self.p2.reset()
                        self.reset()
                        break
    
    # игра против человека
    def play2(self):
        while not self.isEnd:
            # Player 1
            positions = self.availablePositions()
            p1_action = self.p1.chooseAction(positions, self.board, self.playerSymbol)
            # выполняем действие и обновляем состояние поля
            self.updateState(p1_action)
            self.showBoard()
            # проверяем, не закончена ли игра
            win = self.winner()
            if win is not None:
                if win == 1:
                    print(self.p1.name, "выиграл! Смирись, смертный!")
                else:
                    print("Ничья! Неплохо, {}, но ты можешь лучше!".format(self.p2.name))
                self.reset()
                break

            else:
                # Player 2
                positions = self.availablePositions()
                p2_action = self.p2.chooseAction(positions)

                self.updateState(p2_action)
                self.showBoard()
                win = self.winner()
                if win is not None:
                    if win == -1:
                        print(self.p2.name, "выиграл! Ничего себе, да вы настоящий мастер!")
                    else:
                        print("Ничья! Неплохо, {}, но ты можешь лучше!".format(self.p2.name))
                    self.reset()
                    break

    def showBoard(self):
        # p1: x  p2: o
        for i in range(0, BOARD_ROWS):
            print('-------------')
            out = '| '
            for j in range(0, BOARD_COLS):
                if self.board[i, j] == 1:
                    token = 'x'
                if self.board[i, j] == -1:
                    token = 'o'
                if self.board[i, j] == 0:
                    token = ' '
                out += token + ' | '
            print(out)
        print('-------------')


class Player:
    def __init__(self, name, exp_rate=0.3):
        self.name = name
        self.states = []  # записываем все занятые позиции
        self.lr = 0.2
        self.exp_rate = exp_rate
        self.decay_gamma = 0.9
        self.states_value = {}  # состояние -> значение
    
    def getHash(self, board):
        boardHash = str(board.reshape(BOARD_COLS*BOARD_ROWS))
        return boardHash
    
    def chooseAction(self, positions, current_board, symbol):
        if np.random.uniform(0, 1) <= self.exp_rate:
            # выбираем рандомное действие
            idx = np.random.choice(len(positions))
            action = positions[idx]
        else:
            value_max = -999
            for p in positions:
                next_board = current_board.copy()
                next_board[p] = symbol
                next_boardHash = self.getHash(next_board)
                value = 0 if self.states_value.get(next_boardHash) is None else self.states_value.get(next_boardHash)
                # print("value", value)
                if value >= value_max:
                    value_max = value
                    action = p
        # print("{} takes action {}".format(self.name, action))
        return action
    
    # добавляем сохранённое состояние
    def addState(self, state):
        self.states.append(state)
    
    # в конце игры обновляем значения состояний в обратном порядке
    def feedReward(self, reward):
        for st in reversed(self.states):
            if self.states_value.get(st) is None:
                self.states_value[st] = 0
            self.states_value[st] += self.lr*(self.decay_gamma*reward - self.states_value[st])
            reward = self.states_value[st]
            
    def reset(self):
        self.states = []
        
    def savePolicy(self):
        fw = open('policy_' + str(self.name), 'wb')
        pickle.dump(self.states_value, fw)
        fw.close()

    def loadPolicy(self, file):
        fr = open(file,'rb')
        self.states_value = pickle.load(fr)
        fr.close()


class HumanPlayer:
    def __init__(self, name):
        self.name = name 
    
    def chooseAction(self, positions):
        while True:
            row = int(input("Введите номер строки для вашего хода:"))
            col = int(input("Введите номер столбца для вашего хода:"))
            action = (row, col)
            if action in positions:
                return action
    
    def addState(self, state):
        pass
    
    def feedReward(self, reward):
        pass
            
    def reset(self):
        pass


if __name__ == "__main__":
    # обучение
    p1 = Player("p1")
    p2 = Player("p2")

    st = State(p1, p2)
    print("Обучение самого мощного игрока в крестики-нолики...")
    st.play(50000)

    # игра с человеком
    p1 = Player("Компьютер", exp_rate=0)
    p1.loadPolicy("policy_p1")

    p2 = HumanPlayer(input("Введите ваше имя:"))

    st = State(p1, p2)
    st.play2()
