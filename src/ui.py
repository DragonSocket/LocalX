from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Button, Header, Footer, RichLog
from textual.containers import Vertical, Horizontal
from textual.message import Message

# Custom events to decouple UI from Logic
class SetupSubmitted(Message):
    """Событие, когда пользователь нажал 'Start' на экране настройки."""
    def __init__(self, ip: str, port: int, username: str) -> None:
        super().__init__()
        self.ip = ip
        self.port = port
        self.username = username

class MessageSent(Message):
    """Событие, когда пользователь ввел сообщение и нажал Enter."""
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

class SetupScreen(Screen):
    """Экран настройки соединения."""
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="setup-container"):
            yield Input(placeholder="IP Address (e.g. 127.0.0.1)", id="ip")
            yield Input(placeholder="Port (e.g. 1234)", id="port")
            yield Input(placeholder="Your Name", id="username")
            yield Button("Connect", variant="success", id="connect_btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect_btn":
            ip = self.query_one("#ip", Input).value
            port_str = self.query_one("#port", Input).value
            username = self.query_one("#username", Input).value

            if ip and port_str and username:
                try:
                    port = int(port_str)
                    self.post_message(SetupSubmitted(ip, port, username))
                except ValueError:
                    self.notify("Invalid port number!", severity="error")
            else:
                self.notify("Please fill all fields!", severity="error")

class ChatScreen(Screen):
    """Основной экран чата."""
    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(highlight=True, markup=True, id="chat_log")
        with Horizontal():
            yield Input(placeholder="Type a message...", id="input_box")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input_box":
            if event.value.strip():
                self.post_message(MessageSent(event.value.strip()))
                event.input.value = ""  # Clear input

    def add_message_to_log(self, sender: str, message: str, is_me: bool = False) -> None:
        """Метод для внешнего вызова (через контроллер) для обновления лога."""
        log = self.query_one("#chat_log", RichLog)
        prefix = "[bold blue]You:[/bold blue]" if is_me else f"[bold green]{sender}:[/bold green]"
        log.write(f"{prefix} {message}")

class ChatApp(App):
    """Главное приложение Textual."""
    CSS = """
    Screen {
        background: $surface;
    }

    #setup-container {
        align: center middle;
        width: 60%;
        height: auto;
        border: heavy $primary;
        padding: 1 2;
        background: $panel;
    }

    Input {
        margin-bottom: 1;
        background: $surface;
    }

    Button {
        width: 100%;
    }

    #chat_log {
        height: 1fr;
        border: panel $primary;
        margin: 1;
        background: $surface;
    }

    #input_box {
        margin: 1;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        yield SetupScreen()

    def on_setup_submitted(self, event: SetupSubmitted) -> None:
        """Обработка перехода с экрана настройки на экран чата."""
        self.push_screen(ChatScreen())
        # Мы передаем данные через атрибут, чтобы контроллер мог их забрать
        self.config = {
            "ip": event.ip,
            "port": event.port,
            "username": event.username
        }

    def on_message_sent(self, event: MessageSent) -> None:
        """Это событие перехватывается контроллером."""
        pass
