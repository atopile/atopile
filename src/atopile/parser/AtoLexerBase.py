# Original code developed by : Robert Einhorn
# Modified for us in the atopile parser

import sys
from typing import TYPE_CHECKING, Any, Protocol, TextIO

from antlr4 import InputStream, Lexer, Token
from antlr4.Token import CommonToken

if TYPE_CHECKING:

    class GeneratedAtoLexerProtocol(Protocol):
        @property
        def OPEN_PAREN(self) -> int: ...

        @property
        def OPEN_BRACK(self) -> int: ...

        @property
        def OPEN_BRACE(self) -> int: ...

        @property
        def CLOSE_PAREN(self) -> int: ...

        @property
        def CLOSE_BRACK(self) -> int: ...

        @property
        def CLOSE_BRACE(self) -> int: ...

        @property
        def NEWLINE(self) -> int: ...

        @property
        def INDENT(self) -> int: ...

        @property
        def DEDENT(self) -> int: ...

        @property
        def WS(self) -> int: ...

        @property
        def COMMENT(self) -> int: ...

        @property
        def ERRORTOKEN(self) -> int: ...

        @property
        def symbolicNames(self) -> list[str]: ...

        @property
        def _modeStack(self) -> list[str]: ...

        @property
        def _mode(self) -> list[str]: ...
else:
    GeneratedAtoLexerProtocol = Any


class AtoLexerBase(Lexer, GeneratedAtoLexerProtocol):
    def __init__(self, input: InputStream, output: TextIO = sys.stdout):
        super().__init__(input, output)

        # A stack that keeps track of the indentation lengths
        self.__indent_length_stack: list[int]

        # A list where tokens are waiting to be loaded into the token stream
        self.__pending_tokens: list[CommonToken]

        # last pending token types
        self.__previous_pending_token_type: int
        self.__last_pending_token_type_from_default_channel: int

        # The amount of opened parentheses, square brackets or curly braces
        self.__opened: int
        # The amount of opened parentheses and square brackets in the current lexer mode
        self.__paren_or_bracket_opened_stack: list[int]

        self.__was_space_indentation: bool
        self.__was_tab_indentation: bool
        self.__was_indentation_mixed_with_spaces_and_tabs: bool

        self.__cur_token: CommonToken | None  # current (under processing) token
        self.__ffg_token: CommonToken | None  # following (look ahead) token

        self.__INVALID_LENGTH: int = -1
        self.__ERR_TXT: str = " ERROR: "

        self.__init()

    def nextToken(self) -> CommonToken:  # reading the input stream until a return EOF
        self.__check_next_token()
        return self.__pending_tokens.pop(0)  # add the queued token to the token stream

    def reset(self) -> None:
        self.__init()
        super().reset()

    def __init(self) -> None:
        self.__indent_length_stack = []
        self.__pending_tokens = []
        self.__previous_pending_token_type = 0
        self.__last_pending_token_type_from_default_channel = 0
        self.__opened = 0
        self.__paren_or_bracket_opened_stack = []
        self.__was_space_indentation = False
        self.__was_tab_indentation = False
        self.__was_indentation_mixed_with_spaces_and_tabs = False
        self.__cur_token = None
        self.__ffg_token = None

    def __check_next_token(self) -> None:
        if self.__previous_pending_token_type != Token.EOF:
            self.__set_current_and_following_tokens()
            if len(self.__indent_length_stack) == 0:  # We're at the first token
                self.__handle_start_of_input()

            assert self.__cur_token is not None
            match self.__cur_token.type:
                case self.OPEN_PAREN | self.OPEN_BRACK | self.OPEN_BRACE:
                    self.__opened += 1
                    self.__add_pending_token(self.__cur_token)
                case self.CLOSE_PAREN | self.CLOSE_BRACK | self.CLOSE_BRACE:
                    self.__opened -= 1
                    self.__add_pending_token(self.__cur_token)
                case self.NEWLINE:
                    self.__handle_NEWLINE_token()
                case self.ERRORTOKEN:
                    self.__report_lexer_error(
                        "token recognition error at: '" + self.__cur_token.text + "'"
                    )
                    self.__add_pending_token(self.__cur_token)
                case Token.EOF:
                    self.__handle_EOF_token()
                case _:
                    self.__add_pending_token(self.__cur_token)

    def __set_current_and_following_tokens(self) -> None:
        self.__cur_token = (
            super().nextToken() if self.__ffg_token is None else self.__ffg_token
        )

        self.__handle_lexer_modes()

        self.__ffg_token = (
            self.__cur_token
            if self.__cur_token.type == Token.EOF
            else super().nextToken()
        )

    # initialize the _indent_length_stack
    # hide the leading NEWLINE token(s)
    # if exists, find the first statement (not NEWLINE, not EOF token)
    # that comes from the default channel
    # insert a leading INDENT token if necessary
    def __handle_start_of_input(self) -> None:
        assert self.__cur_token is not None

        # initialize the stack with a default 0 indentation length
        self.__indent_length_stack.append(0)  # this will never be popped off
        while self.__cur_token.type != Token.EOF:
            if self.__cur_token.channel == Token.DEFAULT_CHANNEL:
                if self.__cur_token.type == self.NEWLINE:
                    # all the NEWLINE tokens must be ignored before the first statement
                    self.__hide_and_add_pending_token(self.__cur_token)
                else:  # We're at the first statement
                    self.__insert_leading_indent_token()
                    # continue the processing of the
                    # current token with __check_next_token()
                    return
            else:
                self.__add_pending_token(
                    self.__cur_token
                )  # it can be WS, EXPLICIT_LINE_JOINING or COMMENT token
            self.__set_current_and_following_tokens()
        # continue the processing of the EOF token with __check_next_token()

    def __insert_leading_indent_token(self) -> None:

        if self.__previous_pending_token_type == self.WS:
            prev_token: CommonToken = self.__pending_tokens[-1]  # WS token
            if (
                self.__get_indentation_length(prev_token.text) != 0
            ):  # there is an "indentation" before the first statement
                err_msg: str = "first statement indented"
                self.__report_lexer_error(err_msg)
                # insert an INDENT token before the first statement to
                # raise an 'unexpected indent' error later by the parser
                assert self.__cur_token is not None
                self.__create_and_add_pending_token(
                    self.INDENT,
                    Token.DEFAULT_CHANNEL,
                    self.__ERR_TXT + err_msg,
                    self.__cur_token,
                )

    def __handle_NEWLINE_token(self) -> None:
        assert self.__cur_token is not None
        assert self.__ffg_token is not None

        if (
            self.__opened > 0
        ):  # We're in an implicit line joining, ignore the current NEWLINE token
            self.__hide_and_add_pending_token(self.__cur_token)
        else:
            nl_token: CommonToken = (
                self.__cur_token.clone()
            )  # save the current NEWLINE token
            is_looking_ahead: bool = self.__ffg_token.type == self.WS
            if is_looking_ahead:
                self.__set_current_and_following_tokens()  # set the next two tokens

            match self.__ffg_token.type:
                case self.NEWLINE | self.COMMENT:
                    # We're before a blank line or a comment
                    # or type comment or a type ignore comment
                    self.__hide_and_add_pending_token(
                        nl_token
                    )  # ignore the NEWLINE token
                    if is_looking_ahead:
                        self.__add_pending_token(self.__cur_token)  # WS token
                case other:
                    self.__add_pending_token(nl_token)
                    if (
                        is_looking_ahead
                    ):  # We're on a whitespace(s) followed by a statement
                        indentation_length: int = (
                            0
                            if self.__ffg_token.type == Token.EOF
                            else self.__get_indentation_length(self.__cur_token.text)
                        )

                        if indentation_length != self.__INVALID_LENGTH:
                            self.__add_pending_token(self.__cur_token)  # WS token
                            self.__insert_indent_or_dedent_token(
                                indentation_length
                            )  # may insert INDENT token or DEDENT token(s)
                        else:
                            self.__report_error(
                                "inconsistent use of tabs and spaces in indentation"
                            )
                    else:
                        # We're at a newline followed by a statement
                        # (there is no whitespace before the statement)
                        self.__insert_indent_or_dedent_token(
                            0
                        )  # may insert DEDENT token(s)

    def __insert_indent_or_dedent_token(self, indent_length: int) -> None:
        assert self.__indent_length_stack is not None
        assert self.__ffg_token is not None

        prev_indent_length: int = self.__indent_length_stack[-1]  # peek()
        if indent_length > prev_indent_length:
            self.__create_and_add_pending_token(
                self.INDENT, Token.DEFAULT_CHANNEL, None, self.__ffg_token
            )
            self.__indent_length_stack.append(indent_length)
        else:
            while (
                indent_length < prev_indent_length
            ):  # more than 1 DEDENT token may be inserted to the token stream
                self.__indent_length_stack.pop()
                prev_indent_length = self.__indent_length_stack[-1]  # peek()
                if indent_length <= prev_indent_length:
                    self.__create_and_add_pending_token(
                        self.DEDENT, Token.DEFAULT_CHANNEL, None, self.__ffg_token
                    )
                else:
                    self.__report_error("inconsistent dedent")

    def __handle_lexer_modes(self) -> None:
        if self._modeStack:
            assert self.__cur_token is not None
            match self.__cur_token.type:
                case self.OPEN_BRACE:
                    self.pushMode(Lexer.DEFAULT_MODE)
                    self.__paren_or_bracket_opened_stack.append(0)
                case self.OPEN_PAREN | self.OPEN_BRACK:
                    # https://peps.python.org/pep-0498/#lambdas-inside-expressions
                    self.__paren_or_bracket_opened_stack[-1] += (
                        1  # increment the last element (peek() + 1)
                    )
                case self.CLOSE_PAREN | self.CLOSE_BRACK:
                    self.__paren_or_bracket_opened_stack[-1] -= (
                        1  # decrement the last element (peek() - 1)
                    )
                case self.CLOSE_BRACE:
                    match self._mode:
                        case Lexer.DEFAULT_MODE:
                            self.popMode()
                            self.__paren_or_bracket_opened_stack.pop()
                        case _:
                            self.__report_lexer_error(
                                "f-string: single '}' is not allowed"
                            )

    def __insert_trailing_tokens(self) -> None:
        match self.__last_pending_token_type_from_default_channel:
            case self.NEWLINE | self.DEDENT:
                pass  # no trailing NEWLINE token is needed
            case _:
                # insert an extra trailing NEWLINE token that serves
                # as the end of the last statement
                assert self.__ffg_token is not None
                self.__create_and_add_pending_token(
                    self.NEWLINE, Token.DEFAULT_CHANNEL, None, self.__ffg_token
                )  # _ffg_token is EOF
        self.__insert_indent_or_dedent_token(
            0
        )  # Now insert as much trailing DEDENT tokens as needed

    def __handle_EOF_token(self) -> None:
        assert self.__cur_token is not None

        if self.__last_pending_token_type_from_default_channel > 0:
            # there was statement in the input (leading NEWLINE tokens are hidden)
            self.__insert_trailing_tokens()
        self.__add_pending_token(self.__cur_token)

    def __hide_and_add_pending_token(self, ctkn: CommonToken) -> None:
        ctkn.channel = Token.HIDDEN_CHANNEL
        self.__add_pending_token(ctkn)

    def __create_and_add_pending_token(
        self, ttype: int, channel: int, text: str | None, sample_token: CommonToken
    ) -> None:
        ctkn: CommonToken = sample_token.clone()
        ctkn.type = ttype
        ctkn.channel = channel
        ctkn.stop = sample_token.start - 1
        ctkn.text = "<" + self.symbolicNames[ttype] + ">" if text is None else text

        self.__add_pending_token(ctkn)

    def __add_pending_token(self, ctkn: CommonToken) -> None:
        # save the last pending token type because the _pending_tokens
        # list can be empty by the nextToken()
        self.__previous_pending_token_type = ctkn.type
        if ctkn.channel == Token.DEFAULT_CHANNEL:
            self.__last_pending_token_type_from_default_channel = (
                self.__previous_pending_token_type
            )
        self.__pending_tokens.append(ctkn)

    def __get_indentation_length(
        self, indentText: str
    ) -> int:  # the indentText may contain spaces, tabs or form feeds
        TAB_LENGTH: int = 8  # the standard number of spaces to replace a tab to spaces
        length: int = 0
        ch: str
        for ch in indentText:
            match ch:
                case " ":
                    self.__was_space_indentation = True
                    length += 1
                case "\t":
                    self.__was_tab_indentation = True
                    length += TAB_LENGTH - (length % TAB_LENGTH)
                case "\f":  # form feed
                    length = 0

        if self.__was_tab_indentation and self.__was_space_indentation:
            if not self.__was_indentation_mixed_with_spaces_and_tabs:
                self.__was_indentation_mixed_with_spaces_and_tabs = True
                length = self.__INVALID_LENGTH  # only for the first inconsistent indent
        return length

    def __report_lexer_error(self, err_msg: str) -> None:
        assert self.__cur_token is not None

        self.getErrorListenerDispatch().syntaxError(
            self,
            self.__cur_token,
            self.__cur_token.line,
            self.__cur_token.column,
            " LEXER" + self.__ERR_TXT + err_msg,
            None,
        )

    def __report_error(self, err_msg: str) -> None:
        assert self.__ffg_token is not None

        self.__report_lexer_error(err_msg)

        # the ERRORTOKEN will raise an error in the parser
        self.__create_and_add_pending_token(
            self.ERRORTOKEN,
            Token.DEFAULT_CHANNEL,
            self.__ERR_TXT + err_msg,
            self.__ffg_token,
        )
