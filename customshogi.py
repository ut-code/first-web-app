"""
動作環境: Python3.10以上

TODO: (モジュールの)ドキュメントをまとめる
"""

# TODO: 成りの追加(設定可能にする)
# TODO: 持ち駒機能の追加(切り替え可能にする)
# TODO: 初手の動きの追加(設定可能にする)

from __future__ import annotations
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from enum import Enum, auto
from typing import Any, Optional, Literal


def choose_by_user(option: set[str], *, msg="choose from following choises: "):
    """ユーザーに選択肢を表示し、選択を行わせる"""
    while True:
        print(msg, end='')
        print(*sorted(option), sep=", ")
        choice = input()
        if choice in option:
            return choice
        print(f"invalid input: {choice}")


# 盤についての前提条件
#     - マスは正方形であり、頂点が集まるように敷き詰められている
#     - 一マスに存在しうる駒は高々1つ
#     - 駒はマス内もしくは駒台上にのみ存在する
#     - 走り駒は原則、盤の欠けの上を走ることはできない


class Coordinate(ABC):
    """二次元座標の基底クラス
    座標の負の値は、負のインデックスとして解釈される。

    Constructor Params:
        y: +は前, -は後ろ
        x: +は右, -は左
    """
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{self.y, self.x}"

    __str__ = __repr__

    def __init__(self, y: int, x: int) -> None:
        if not isinstance(y, int):
            raise TypeError("y must be an interger")
        if not isinstance(x, int):
            raise TypeError("x must be an interger")
        self.__y = y
        self.__x = x

    @property
    def y(self):
        """前後方向の座標
        +は前, -は後ろ
        """
        return self.__y

    @property
    def x(self):
        """左右方向の座標
        +は右, -は左
        """
        return self.__x

    def __add__(self, __o: object):
        if not isinstance(__o, Coordinate):
            raise TypeError
        return type(self)(self.y+__o.y, self.x+__o.x)

    def __copy__(self):
        return type(self)(self.y, self.x)

    def __hash__(self) -> int:
        return hash((self.__y, self.__x, type(self)))

    def __eq__(self, __value: object) -> bool:
        if type(__value) != type(self):
            return False
        return (self.x==__value.x) and (self.y==__value.y)

class AbsoluteCoordinate(Coordinate):
    """盤面の座標を表すクラス
    座標の負の値は、負のインデックスとして解釈される。

    Constructor Params:
        y: +は前, -は後ろ
        x: +は右, -は左
    """
    def __add__(self, __o: object):
        if isinstance(__o, AbsoluteCoordinate):
            raise TypeError("cannot add two absolute coordinates")
        return super().__add__(__o)

    __radd__ = __add__

    @property
    def x_inverted(self):
        """x座標を反転させた座標(y, x)を返す"""
        return type(self)(self.y, ~self.x)

    @property
    def y_inverted(self):
        """y座標を反転させた座標(y, x)を返す"""
        return type(self)(~self.y, self.x)

    def __neg__(self):
        return type(self)(~self.y, ~self.x)

    __invert__ = __neg__

    @property
    def full_inverted(self):
        """x, y座標をそれぞれ反転させた座標(y, x)を返す"""
        return -self

    def __pos__(self):
        return super().__copy__

    def normalized_by(self, board: IBoard):
        """盤面の大きさに合わせて、負のインデックスを標準形に直す"""
        return type(self)(self._normalizer(self.y, board.height), self._normalizer(self.x, board.width))

    @staticmethod
    def _normalizer(target: int, standard: int) -> int:
        if target < -standard or standard <= target:
            raise ValueError(f"target coordinate {target} is out of range{-standard, standard}")
        if target < 0:
            return target + standard
        return target

class RelativeCoordinate(Coordinate):
    """盤面における相対座標を表すクラス"""
    def __abs__(self) -> int:
        return max(abs(self.y), abs(self.x))

    def __add__(self, __o: object):
        if isinstance(__o, RelativeCoordinate):
            return super().__add__(__o)
        return NotImplemented

    @property
    def x_inverted(self):
        """x座標を反転させた座標(y, x)を返す"""
        return type(self)(self.y, -self.x)

    @property
    def y_inverted(self):
        """y座標を反転させた座標(y, x)を返す"""
        return type(self)(-self.y, self.x)

    def __neg__(self):
        return type(self)(-self.y, -self.x)

    __invert__ = __neg__

    @property
    def full_inverted(self):
        """x, y座標をそれぞれ反転させた座標(y, x)を返す"""
        return -self

    def __pos__(self):
        return super().__copy__()

    @property
    def upside_right(self):
        """直線y=xに対して対称に反転させた座標(y, x)を返す"""
        return type(self)(self.x, self.y)

    @property
    def upside_left(self):
        """直線y=-xに対して対称に反転させた座標(y, x)を返す"""
        return type(self)(-self.x, -self.y)


class Controller2P(Enum):
    """駒・ターンのコントローラーを示す

    INDEPENDENT: その他(未使用)
    WHITE: 先手
    BLACK: 後手

    行列演算`@`によって、(左辺)から見た(右辺)の素性を示す`Relation2P`を返す
    """
    INDEPENDENT = auto()
    WHITE = auto()
    BLACK = auto()

    def __matmul__(self, __o: object) -> Relation:
        if self is Controller2P.INDEPENDENT:
            raise NotImplementedError("moving independent piece is not implemented yet")
        if __o is None:
            return Relation.TO_BLANK
        if not isinstance(__o, Controller2P):
            raise TypeError
        if __o is Controller2P.INDEPENDENT:
            raise NotImplementedError("moving independent piece is not implemented yet")
        if self is __o:
            return Relation.FRIEND
        return Relation.ENEMY

    def next_player(self):
        """ターン順で次のプレイヤー"""
        if self is Controller2P.WHITE:
            return Controller2P.BLACK
        if self is Controller2P.BLACK:
            return Controller2P.WHITE
        raise NotImplementedError("next turn of absent")


class Relation(Enum):
    """駒同士の関係を示す

    ENEMY: 敵(コントローラーが異なる)
    FRIEND: 味方(コントローラーが同一)
    TO_BLANK: 移動先に駒がない
    """
    FRIEND = auto()
    ENEMY = auto()
    TO_BLANK = auto()


class Approachability(Enum):
    """あるマスに対する駒の移動の可否

    用語を以下に定める
        着地: その地点に駒を移動させる。当該のマスにあった駒は捕獲され、移動した駒のコントローラーの持ち駒となる。その移動の制御者によるさらなる移動先の探索は中止され、制御は次に移る。
        通過: その地点を駒の有効な移動先として登録せずに、制御者を変更せずにその次のマスから探索を続行する。

    REJECT: 着地、通過ともに不可
    END: 着地は可、通過は不可
    ONLY_PASS: 着地は不可、通過は可
    CONTINUE: 着地、通過ともに可
    """
    # (そのマスに止まれるか, そのマスから先に進めるか)
    REJECT = (False, False)
    END = (True, False)
    ONLY_PASS = (False, True)
    CONTINUE = (True, True)

    def __init__(self, can_land: bool, can_go_over: bool) -> None:
        self.__can_land = can_land
        self.__can_go_over = can_go_over

    @property
    def can_land(self):
        """着地可能かを示すブール値"""
        return self.__can_land

    @property
    def can_go_over(self):
        """通過可能かを示すブール値"""
        return self.__can_go_over


class IMove(ABC):
    """駒の動きの静的な定義の表現のインタフェース"""
    @abstractmethod
    def coordinates_in_controller(self, controller: Controller2P) -> Any:
        """駒がそのコントローラーの下で動ける方向を示す"""

    @abstractmethod
    def valid_destination(
            self,
            board: IBoard,
            controller: Controller2P,
            current_coordinate: AbsoluteCoordinate,
        ) -> set[AbsoluteCoordinate]:
        """諸々から、有効な移動先を返す"""


class IElementalMove(ABC):
    """IMoveDefinitionの子のうち、それらによって初期化しないもの"""
    @abstractmethod
    def approachability(
            self,
            relation: Relation,
        ) -> Approachability:
        """移動先のマスの駒のコントローラーを参照し、そこに対する挙動を返す"""


class LeaperMove(IMove, IElementalMove):
    """Leaper(跳び駒)の動きの実装"""
    def __init__(
            self,
            coordinates: Iterable[RelativeCoordinate],
            *,
            symmetry: Literal['none', 'lr', 'fblr', 'oct'] = 'none',
        ) -> None:
        self.__coordinates: set[RelativeCoordinate] = set(coordinates)
        if symmetry in ('lr', 'fblr', 'oct'):
            self.__coordinates.update({coord.x_inverted for coord in self.__coordinates})
            if symmetry in ('fblr', 'oct'):
                self.__coordinates.update({coord.y_inverted for coord in self.__coordinates})
                if symmetry == 'oct':
                    self.__coordinates.update({coord.upside_left for coord in self.__coordinates})

        self.approachability_mapping = {
            Relation.FRIEND: Approachability.REJECT,
            Relation.ENEMY: Approachability.END,
            Relation.TO_BLANK: Approachability.CONTINUE,
        }

    def derive(
            self,
            coordinates: Iterable[RelativeCoordinate] = ...,
            *,
            symmetry: Literal['none', 'lr', 'fblr', 'oct'] = 'none',
        ) -> None:
        """自身をコピーしたものを返す
        ただし、引数が与えられたものについては上書きし、
        Noneが与えられたものについてはデフォルトの設定に戻す
        """
        if coordinates is ...:
            coordinates = self.__coordinates
        return self.__class__(
            coordinates,
            symmetry=symmetry,
        )

    def approachability(
            self,
            relation: Relation,
        ) -> Approachability:
        return self.approachability_mapping[relation]

    def coordinates_in_controller(self, controller: Controller2P) -> set[RelativeCoordinate]:
        if controller is Controller2P.WHITE:
            return self.__coordinates
        if controller is Controller2P.BLACK:
            return {-coordinate for coordinate in self.__coordinates}
        return set()

    def valid_destination(
            self,
            board: IBoard,
            controller: Controller2P,
            current_coordinate: AbsoluteCoordinate,
        ) -> set[AbsoluteCoordinate]:
        destinations: set[AbsoluteCoordinate] = set()
        for movement in self.coordinates_in_controller(controller):
            new_coordinate = current_coordinate + movement
            if not board.includes(new_coordinate):
                continue
            target_square = board[new_coordinate]
            if target_square.is_excluded:
                continue
            if target_square.piece:
                relation = controller @ target_square.piece.controller
            else:
                relation = Relation.TO_BLANK
            if self.approachability(relation).can_land:
                destinations.add(new_coordinate)
        return destinations


class RiderMove(IMove, IElementalMove):
    """Rider(走り駒)の動きの実装"""
    def __init__(
            self,
            coordinate_to_dist: Mapping[RelativeCoordinate, int],
            *,
            symmetry: Literal['none', 'lr', 'fblr', 'oct'] = 'none',
        ) -> None:
        self.__coordinate_to_dist: dict[RelativeCoordinate, int] = defaultdict(int, coordinate_to_dist)

        if symmetry in ('lr', 'fblr', 'oct'):
            def adopt_dist(a: int, b: int):
                if a < 0 or b < 0:
                    return -1
                return max(a, b)
            for coord, dist in set(self.__coordinate_to_dist.items()):
                self.__coordinate_to_dist[coord.x_inverted] \
                    = adopt_dist(self.__coordinate_to_dist[coord.x_inverted], dist)
            if symmetry in ('fblr', 'oct'):
                for coord, dist in set(self.__coordinate_to_dist.items()):
                    self.__coordinate_to_dist[coord.y_inverted] \
                        = adopt_dist(self.__coordinate_to_dist[coord.x_inverted], dist)
                if symmetry == 'oct':
                    for coord, dist in set(self.__coordinate_to_dist.items()):
                        self.__coordinate_to_dist[coord.upside_left] \
                            = adopt_dist(self.__coordinate_to_dist[coord.x_inverted], dist)

        self.approachability_mapping = {
            Relation.FRIEND: Approachability.REJECT,
            Relation.ENEMY: Approachability.END,
            Relation.TO_BLANK: Approachability.CONTINUE,
        }

    def derive(
            self,
            coordinate_to_dist: Mapping[RelativeCoordinate, int],
            *,
            symmetry: Literal['none', 'lr', 'fblr', 'oct'] = 'none',
        ) -> None:
        """自身をコピーしたものを返す
        ただし、引数が与えられたものについては上書きし、
        Noneが与えられたものについてはデフォルトの設定に戻す
        """
        if coordinate_to_dist is ...:
            coordinate_to_dist = self.__coordinate_to_dist
        return self.__class__(
            coordinate_to_dist,
            symmetry=symmetry,
        )

    def approachability(
            self,
            relation: Relation,
        ) -> Approachability:
        return self.approachability_mapping[relation]

    def coordinates_in_controller(self, controller: Controller2P) -> dict[RelativeCoordinate, int]:
        if controller is Controller2P.WHITE:
            return self.__coordinate_to_dist
        if controller is Controller2P.BLACK:
            return {-coordinate: dist for coordinate, dist in self.__coordinate_to_dist.items()}
        return {}

    def valid_destination(
            self,
            board: IBoard,
            controller: Controller2P,
            current_coordinate: AbsoluteCoordinate,
        ) -> set[AbsoluteCoordinate]:
        destinations: set[AbsoluteCoordinate] = set()
        for movement, max_dist in self.coordinates_in_controller(controller).items():
            new_coordinate = current_coordinate
            if max_dist < 0:
                max_dist = max(board.height, board.width)
            for _ in range(max_dist):
                new_coordinate += movement
                if not board.includes(new_coordinate):
                    break
                target_square = board[new_coordinate]
                if target_square.is_excluded:
                    break
                if target_square.piece:
                    relation = controller @ target_square.piece.controller
                else:
                    relation = Relation.TO_BLANK
                if self.approachability(relation).can_land:
                    destinations.add(new_coordinate)
                if not self.approachability(relation).can_go_over:
                    break
        return destinations


class MoveParallelJoint(IMove):
    """複数の動きを合わせた動きを作る"""
    def __init__(self, *move: IMove) -> None:
        self.move = move

    def coordinates_in_controller(self, controller: Controller2P) -> set[RelativeCoordinate]:
        return set().union(*(move_element.coordinates_in_controller(controller) for move_element in self.move))

    def valid_destination(
            self,
            board: IBoard,
            controller: Controller2P,
            current_coordinate: AbsoluteCoordinate
        ) -> set[AbsoluteCoordinate]:
        return set().union(*(move_element.valid_destination(board, controller, current_coordinate) for move_element in self.move))



class IPiece(ABC):
    """駒の抽象クラス"""
    def __str__(self) -> str:
        return f"{self.NAME}({self.controller})"

    def __init__(
            self,
            controller: Controller2P,
        ) -> None:
        self.controller = controller

    @property
    def SYMBOL_COLORED(self):
        """プレイヤーによって大文字, 小文字の表示を変えるようにしたSYMBOL
        盤面の表示に使う
        """
        if self.controller is Controller2P.WHITE:
            return self.SYMBOL.upper()
        if self.controller is Controller2P.BLACK:
            return self.SYMBOL.lower()
        return self.SYMBOL

    @property
    def NAME(self) -> str:
        """name of piece"""
        return self.__class__.__name__

    @property
    @abstractmethod
    def MOVE(self) -> IMove:
        """move definition of piece"""

    @property
    def ROYALTY(self) -> bool:
        """if True, this piece is royal"""
        return False

    @property
    @abstractmethod
    def SYMBOL(self) -> str:
        """a character that represents this piece"""

    def valid_destination(
            self,
            board: IBoard,
            my_coordinate: AbsoluteCoordinate
        ) -> set[AbsoluteCoordinate]:
        """諸々から、有効な移動先を返す"""
        return self.MOVE.valid_destination(board, self.controller, my_coordinate)
        # 以下、もともとの構想
        # cls.MOVEに従って動ける場所を表示する
        # -> クリックでそこに移動し、(駒を取ることを含む段数が)二段以上だったら次の入力を受け付ける
        # このとき、キャンセルボタンで巻き戻せるようにする
        # 諸々正常に完了したら、それを全体に反映し、確定する


class Square:
    """盤の中のマス"""
    def __init__(
            self,
            piece: Optional[IPiece] = None,
            *,
            is_excluded: bool = False,
        ) -> None:
        self.piece = piece
        self.is_excluded = is_excluded

    def show_to_console(self) -> str:
        """マスの状態をコンソールに1文字で表示する"""
        if self.is_excluded:
            return '#'
        if self.piece is None:
            return ' '
        return self.piece.SYMBOL_COLORED


class IBoard(ABC):
    """盤の抽象クラス"""
    height: int
    width: int
    board: list[list[Square]]
    piece_in_board_index: dict[Controller2P, dict[type[IPiece], set[AbsoluteCoordinate]]]
    piece_stands: dict[Controller2P, Counter[type[IPiece]]]

    def __getitem__(self, __key: AbsoluteCoordinate) -> Square:
        return self.board[__key.y][__key.x]
    def __setitem__(self, __key: AbsoluteCoordinate, __value: Any):
        self.board[__key.y][__key.x] = __value

    def includes(self, coord: AbsoluteCoordinate) -> bool:
        """座標が盤面の中に入っているかを判定する"""
        return (0 <= coord.y < self.height) and (0 <= coord.x < self.width)

    @staticmethod
    def square_referer_from_str(referer_str: str) -> AbsoluteCoordinate:
        """棋譜の表記から座標に変換する"""
        x, y = referer_str[0], referer_str[1:]
        return AbsoluteCoordinate(int(y)-1, ord(x)-97)

    @staticmethod
    def square_referer_to_str(coord: AbsoluteCoordinate) -> str:
        """座標から棋譜の表記に変換する"""
        return f"{chr(97+coord.x)}{coord.y+1}"


class MatchBoard(IBoard):
    """試合用のボード"""
    def __init__(
            self,
            height: int,
            width: int,
            initial_position: Mapping[AbsoluteCoordinate, IPiece],
            excluded_square: Iterable[AbsoluteCoordinate] = (),
            *,
            lr_symmetry: bool = False,
            wb_symmetry: Literal['none', 'face', 'cross'] = 'none',
        ) -> None:
        if not isinstance(height, int):
            raise TypeError("height must be an positive interger")
        if not isinstance(width, int):
            raise TypeError("width must be an positive interger")
        if wb_symmetry not in ('none', 'face', 'cross'):
            raise TypeError(f"{wb_symmetry} is improper value for wb_symmetry")
        self.turn_player = Controller2P.WHITE
        self.height = height
        self.width = width
        # 駒がない状態の盤面を生成
        self.board = [[Square(None) for _ in range(self.width)] for _ in range(self.height)]
        self.piece_stands = {Controller2P.WHITE: Counter(), Controller2P.BLACK: Counter()}
        self.piece_in_board_index = {
            Controller2P.WHITE: defaultdict(set),
            Controller2P.BLACK: defaultdict(set),
        }
        # initial_piecesを元に盤面に駒を置いていく
        excluded_square = {position.normalized_by(self) for position in excluded_square}
        if lr_symmetry:
            initial_position_x_inverted = {
                position.x_inverted.normalized_by(self): piece for position, piece in initial_position.items()
            }
            initial_position = initial_position_x_inverted | initial_position
            excluded_square |= {position.x_inverted.normalized_by(self) for position in excluded_square}
        if wb_symmetry == 'face':
            initial_position_face = {
                position.y_inverted.normalized_by(self): type(piece)(piece.controller.next_player()) for position, piece in initial_position.items()
            }
            initial_position = initial_position_face | initial_position
            excluded_square |= {position.y_inverted.normalized_by(self) for position in excluded_square}
        elif wb_symmetry == 'cross':
            initial_position_cross = {
                (~position).normalized_by(self): type(piece)(piece.controller.next_player()) for position, piece in initial_position.items()
            }
            initial_position = initial_position_cross | initial_position
            excluded_square |= {(~position).normalized_by(self) for position in excluded_square}
        for square in excluded_square:
            self[square].is_excluded = True
        for position, piece in initial_position.items():
            self.add_piece_to_board(type(piece), piece.controller, position)

    @property
    def coords_iterator(self):
        """座標の一覧のイテレータ"""
        return (AbsoluteCoordinate(h, w) for h in range(self.height) for w in range(self.width))

    def show_to_console(self):
        """コンソールに盤面を表示する"""
        h_digit = len(str(self.height+1))
        horizontal_line = '-' * (h_digit-1) + '-+' * (self.width+1)
        column_indicator = ' '*h_digit + '|' + '|'.join(chr(97+w) for w in range(self.width)) + '|'
        print()
        print(column_indicator)
        for h in range(self.height-1, -1, -1):
            print(horizontal_line)
            print(format(h+1, f'#{h_digit}')+'|'+'|'.join((
                self[AbsoluteCoordinate(h, w)].show_to_console()
            ) for w in range(self.width))+'|')
        print(horizontal_line)

    def is_game_terminated(self) -> tuple[bool, Controller2P]:
        """(ゲームが終了したかの真偽値, 勝者)"""
        loser = set()
        for controller in (Controller2P.WHITE, Controller2P.BLACK):
            if not any(len(v) for (k, v) in self.piece_in_board_index[controller].items() if k.ROYALTY):
                loser.add(controller)
        if not loser:
            return (False, Controller2P.INDEPENDENT)
        if len(loser) == 2:
            return (True, Controller2P.INDEPENDENT)
        if Controller2P.WHITE in loser:
            return (True, Controller2P.BLACK)
        if Controller2P.BLACK in loser:
            return (True, Controller2P.WHITE)
        raise ValueError("something unexpected occured")

    def add_piece_to_stand(self, kind: type[IPiece], controller: Controller2P) -> None:
        """駒台に駒を置く"""
        self.piece_stands[controller][kind] += 1

    def add_piece_to_board(
            self,
            kind: type[IPiece],
            controller: Controller2P,
            coord: AbsoluteCoordinate,
            *,
            collision: Literal['raise', 'overwrite', 'skip'] = 'raise',
        ) -> None:
        """盤面に駒を置く"""
        if self[coord].is_excluded and collision != 'skip':
            raise ValueError("cannot set a piece to excluded square")
        if self[coord].piece is not None:
            if collision == 'raise':
                raise ValueError(f"piece is already in {coord}")
            if collision == 'skip':
                return
        self[coord].piece = kind(controller)
        self.piece_in_board_index[controller][kind].add(coord)

    def remove_piece_from_stand(self, kind: type[IPiece], controller: Controller2P):
        """駒台から駒を取り除く"""
        active_piece_stand = self.piece_stands[controller]
        if active_piece_stand[kind] == 0:
            raise ValueError(f"{kind} is not in piece stand")
        active_piece_stand[kind] -= 1

    def remove_piece_from_board(self, coord: AbsoluteCoordinate) -> None:
        """盤面から駒を取り除く"""
        piece = self[coord].piece
        if not piece:
            raise ValueError("removing piece from None")
        self[coord].piece = None
        self.piece_in_board_index[piece.controller][type(piece)].remove(coord)

    def move_destination_from(self, coordinate: AbsoluteCoordinate) -> set[AbsoluteCoordinate]:
        """移動元の座標から、移動先として有効な座標を返す"""
        target_piece = self[coordinate].piece
        if target_piece is None:
            return set()
        return target_piece.valid_destination(self, coordinate)

    def drop_destination(self) -> set[AbsoluteCoordinate]:
        """駒を打つ先として有効な座標を返す"""
        return set(filter(
            lambda coord: (not self[coord].is_excluded) and (self[coord].piece is None),
            self.coords_iterator,
        ))

    def move(self, depart_coord: AbsoluteCoordinate, arrive_coord: AbsoluteCoordinate):
        """駒を実際に動かす"""
        moving_piece = self[depart_coord].piece
        captured_piece = self[arrive_coord].piece
        if captured_piece:
            self.add_piece_to_stand(type(captured_piece), moving_piece.controller)
            self.remove_piece_from_board(arrive_coord)
        self.add_piece_to_board(type(moving_piece), moving_piece.controller, arrive_coord)
        self.remove_piece_from_board(depart_coord)

    def drop(self, kind: type[IPiece], coord: AbsoluteCoordinate):
        """駒を打つ"""
        self.add_piece_to_board(kind, self.turn_player, coord)
        self.remove_piece_from_stand(kind, self.turn_player)

    def promote(self, kind: type[IPiece], coord: AbsoluteCoordinate) -> None:
        """[coord]の駒が[kind]の駒に成る"""
        controller = self[coord].piece.controller
        self.remove_piece_from_board(coord)
        self.add_piece_to_board(kind, controller, coord)


    def game(self):
        """試合を行う"""
        while not self.is_game_terminated()[0]:
            self.show_to_console()
            starting_coord = set.union(*({self.square_referer_to_str(k) for k in i} for i in self.piece_in_board_index[self.turn_player].values()))
            while True:
                depart_coord_str = choose_by_user(starting_coord.union({'r'}))
                if depart_coord_str != 'r':
                    depart_coord = self.square_referer_from_str(depart_coord_str)
                    destination = {self.square_referer_to_str(j) for j in self.move_destination_from(depart_coord)}
                    arrive_coord_str = choose_by_user(destination.union({'r'}))
                    if arrive_coord_str != 'r':
                        arrive_coord = self.square_referer_from_str(arrive_coord_str)
                        self.move(depart_coord, arrive_coord)
                        break
                    print("re-selecting...")
            self.turn_player = self.turn_player.next_player()
        self.show_to_console()
        print(f"game end: winner is {self.is_game_terminated()[1]}")



class King(IPiece):
    NAME = "King"
    MOVE = LeaperMove([RelativeCoordinate(1, 0), RelativeCoordinate(1, 1)], symmetry='oct')
    ROYALTY = True
    SYMBOL = 'k'

class Qween(IPiece):
    NAME = "Qween"
    MOVE = RiderMove({RelativeCoordinate(1, 0): -1, RelativeCoordinate(1, 1): -1}, symmetry='oct')
    ROYALTY = False
    SYMBOL = 'q'

class Bishop(IPiece):
    NAME = "Bishop"
    MOVE = RiderMove({RelativeCoordinate(1, 1): -1}, symmetry='fblr')
    ROYALTY = False
    SYMBOL = 'b'

class Rook(IPiece):
    NAME = "Rook"
    MOVE = RiderMove({RelativeCoordinate(1, 0): -1}, symmetry='oct')
    ROYALTY = False
    SYMBOL = 'r'

class Knight(IPiece):
    NAME = "Knight"
    MOVE = LeaperMove([RelativeCoordinate(2, 1)], symmetry='oct')
    ROYALTY = False
    SYMBOL = "n"

class Pawn(IPiece):
    NAME = "Pawn"
    MOVE = LeaperMove([RelativeCoordinate(1, 0)], symmetry='none')
    ROYALTY = False
    SYMBOL = "p"


if __name__ == '__main__':
    initial_piece_position = {
        AbsoluteCoordinate(0, 3): King(Controller2P.WHITE),
        AbsoluteCoordinate(0, 4): Qween(Controller2P.WHITE),
        AbsoluteCoordinate(0, 0): Rook(Controller2P.WHITE),
        AbsoluteCoordinate(0, 2): Bishop(Controller2P.WHITE),
        AbsoluteCoordinate(0, 1): Knight(Controller2P.WHITE),
        **{AbsoluteCoordinate(1, n): Pawn(Controller2P.WHITE) for n in range(4)},
    }
    play_board = MatchBoard(
        height=8,
        width=8,
        initial_position=initial_piece_position,
        lr_symmetry=True,
        wb_symmetry='face',
    )
    play_board.game()
